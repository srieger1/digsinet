#!/usr/bin/python3
import argparse
import os
import time
import copy
import importlib
import re
import sys
import logging
import atexit
import subprocess
import signal

import yaml

from pygnmi.client import gNMIclient

from controllers.controller import Controller
from multiprocessing import Queue
from functools import partial

from deepdiff import DeepDiff

class Digsinet:
    def __init__(self):
        self.args = self.__get_args()
        self.logger = logging.getLogger(__name__)
        if self.args.debug:
            self.logger.setLevel(logging.DEBUG)
            logging.basicConfig(level=logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)
        self.logger.addHandler(logging.StreamHandler())
        self.config = self.__get_config()
        self.procs = []

    def run(self):
        if not self.__is_root():
            print('digsinet must be run as root', file=sys.stderr)
            sys.exit(-1)
        if self.args.reconfigure:
            reconfigureContainers = "--reconfigure"
        else:
            reconfigureContainers = ""

        # declarative model of the real network 
        model = dict()
        model['nodes'] = dict()
        model['siblings'] = dict()
        model['controllers'] = dict[Controller]()
        model['queues'] = dict[Queue]()

        # load controllers for the models
        for controller in self.config['controllers']:
            # import the module
            self.logger.debug("Loading controller " + controller + "...")
            module = importlib.import_module(self.config['controllers'][controller]['module'])
            model['controllers'][controller] = module
        
        # Open and read the topology file for the real network
        with open(self.config['topology']['file'], 'r') as stream:
            # Load the YAML topology file
            clab_topology_definition = yaml.safe_load(stream)
            if clab_topology_definition.get('prefix'):
                self.config['clab_topology_prefix'] = clab_topology_definition['prefix']
            else:
                self.config['clab_topology_prefix'] = "clab"

        for node in clab_topology_definition['topology']['nodes'].items():
            model['nodes'][node[0]] = dict()

        self.procs.append(subprocess.Popen(f"clab deploy {reconfigureContainers} -t {self.config['topology']['file']}", shell=True, preexec_fn=os.setsid))
        
        for sibling in self.config['siblings']:
            # Create a sibling in the model
            model['siblings'][sibling] = dict()
            # create queue for the sibling
            model['queues'][sibling] = Queue()

            # Get the topology for the sibling
            sibling_clab_topo = copy.deepcopy(clab_topology_definition)
            # Update the name in the topology to reflect the sibling
            sibling_clab_topo['name'] = clab_topology_definition['name'] + "_" + sibling
            # Topology adjustments for the sibling

            if self.config['siblings'][sibling] is not None and self.config['siblings'][sibling].get('topology-adjustments'):
                for adjustment in self.config['siblings'][sibling]['topology-adjustments']:
                    match adjustment:
                        case 'node-remove':
                            for node in sibling_clab_topo['topology']['nodes'].copy().items():
                                if re.fullmatch(self.config['siblings'][sibling]['topology-adjustments']['node-remove'], node[0]):
                                    sibling_clab_topo['topology']['nodes'].pop(node[0])

                                # Remove links to removed nodes from the topology
                                for link in sibling_clab_topo['topology']['links']:
                                    if any(endpoint.startswith(node[0] + ":") for endpoint in link['endpoints']):
                                        sibling_clab_topo['topology']['links'].pop(sibling_clab_topo['topology']['links'].index(link))
                        case 'node-add':
                            for node in self.config['siblings'][sibling]['topology-adjustments']['node-add']:
                                node_config = self.config['siblings'][sibling]['topology-adjustments']['node-add'][node]
                                sibling_clab_topo['topology']['nodes'][node] = node_config
                        case 'link-remove':
                            # Remove links from the topology
                            for link in self.config['siblings'][sibling]['topology-adjustments']['link-remove']:
                                sibling_clab_topo['topology']['links'].pop(sibling_clab_topo['topology']['links'].index(link))
                        case 'link-add':
                            # Add links to the topology
                            for link in self.config['siblings'][sibling]['topology-adjustments']['link-add']:
                                sibling_clab_topo['topology']['links'].append(link)
            # Write the sibling topology to a new file
            with open("./" + self.config['name'] + "_sib_" + sibling + ".clab.yml", 'w') as stream:
                yaml.dump(sibling_clab_topo, stream)
            # Set the sibling topology in the model
            model['siblings'][sibling]['clab_topology'] = sibling_clab_topo

            sibling_config = self.config['siblings'].get(sibling)
            # If the sibling config exists and autostart is enabled
            if sibling_config:
                if sibling_config.get('autostart'):
                    # Deploy the sibling topology using Containerlab
                    self.logger.info("Deploying sibling " + sibling + "...")
                    self.procs.append(subprocess.Popen(f"clab deploy {reconfigureContainers} -t {self.config['name']}_sib_{sibling}.clab.yml", shell=True, preexec_fn=os.setsid))
                    model['siblings'][sibling]['running'] = True
        # start controllers for siblings
        for sibling in model['siblings']:
            if model['siblings'][sibling].get('running'):
                # if sibling has a controller defined, start it
                if self.config['siblings'][sibling].get('controller'):
                    self.logger.info("=== Start Controller for " + sibling + "...")
                    configured_sibling_controller = self.config['siblings'][sibling]['controller']
                    controller_instance = getattr(model['controllers'][configured_sibling_controller], configured_sibling_controller)
                    model['siblings'][sibling]['controller'] = controller_instance(self.config, clab_topology_definition, model, sibling)
        self.logger.info("Starting main loop...")
        while True:
            self.logger.debug("sleeping until next sync interval...")
            time.sleep(self.config['interval'])

            # get gNMI data from the real network
            # could be improved by using subscribe instead of get
            self.logger.debug("<-- Getting gNMI data from the real network...")

            # save old model for comparison until we implement subscriptions etc.
            old_model = dict()
            old_model['nodes'] = copy.deepcopy(model['nodes'])

            port = self.config['gnmi']['port']
            username = self.config['gnmi']['username']
            password = self.config['gnmi']['password']
            for node in clab_topology_definition['topology']['nodes'].items():
                if re.fullmatch(self.config['gnmi']['nodes'], node[0]):
                    host = self.config['clab_topology_prefix'] + "-" + clab_topology_definition['name'] + "-" + node[0]
                    print(f"Host: {host}, Port: {port}, User: {username}, Password: {password}\n")
                    with gNMIclient(target=(host, port), username=username, password=password, insecure=True) as gc:
                        for path in self.config['gnmi']['paths']:
                            result = gc.get(path=[path], datatype=self.config['gnmi']['datatype'])
                            # for strip in config['gnmi']['strip']:
                            #    # result = result.pop(strip)
                            model['nodes'][node[0]][path] = copy.deepcopy(result)

                            # diff old and new model, excluding timestamp
                            diff = DeepDiff(old_model['nodes'], model['nodes'], ignore_order=True, exclude_regex_paths="\['timestamp'\]")

                            # if changes were detected, send an update to the controller queues
                            if diff.tree != {}:
                                for queue in model['queues']:
                                    model['queues'][queue].put({"type": "gNMI notification", 
                                                            "source": "realnet", 
                                                            "node": node, 
                                                            "path": path, 
                                                            "data": result,
                                                            "diff": diff.tree})
        self.cleanup()

    def stop(self):
        self.running = False

    def __is_root(self):
        return os.getuid() == 0

    def __kill_procs(self):
        for proc in self.procs:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        self.procs.clear()
    
    def __get_args(self):
        '''
        creates an argument parser and returns the parsed arguments
        '''
        parser = argparse.ArgumentParser()
        parser.add_argument('--config', help='Config file', default='./digsinet.yml')
        parser.add_argument('--reconfigure', help='Reconfigure existing containerlab containers', action='store_true')
        parser.add_argument('--debug', help='Enable debug logging', action='store_true')
        return parser.parse_args()
    
    def __get_config(self):
        with open(self.args.config, 'r') as stream:
            # Load the YAML config file
            config = yaml.safe_load(stream)
            # add logging config to be used by controllers and apps
            config['logger'] = self.logger
            return config
    
    def cleanup(self):
        self.__kill_procs()
        subprocess.run(f"clab destroy -t {self.config['topology']['file']}", shell=True)
        for sibling in self.config['siblings']:
            sibling_config = self.config['siblings'].get(sibling)
            if sibling_config:
                if sibling_config.get('autostart'):
                    subprocess.run(f"clab destroy -t {self.config['name']}_sib_{sibling}.clab.yml", shell=True)
        
def cleanup(digsinet):
    digsinet.cleanup()
                    
if __name__ == '__main__':
    digsinet = Digsinet()
    atexit.register(cleanup, digsinet)
    digsinet.run()