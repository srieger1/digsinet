#!/usr/bin/python3
import argparse
import os
import time
import copy
import importlib
import re
import logging

import yaml

from pygnmi.client import gNMIclient

from controllers.controller import Controller
from multiprocessing import Queue

from deepdiff import DeepDiff

def main():
    # Create an argument parser
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', help='Config file', default='./digsinet.yml')
    parser.add_argument('--reconfigure', help='Reconfigure existing containerlab containers', action='store_true')
    parser.add_argument('--debug', help='Enable debug logging', action='store_true')
    args = parser.parse_args()

    # If the reconfigure flag is set, clab will be told to reconfigure existing containers
    if args.reconfigure:
        reconfigureContainers = "--reconfigure"
    else:
        reconfigureContainers = ""

    logger = logging.getLogger(__name__)
    # If the debug flag is set, the log level will be set to debug
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logging.basicConfig(level=logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler())

    # Create information model for the real network
    model = dict()
    model['nodes'] = dict()
    model['siblings'] = dict()
    model['controllers'] = dict[Controller]()
    model['queues'] = dict[Queue]()

    # Open and read the config file
    with open(args.config, 'r') as stream:
        # Load the YAML config file
        config = yaml.safe_load(stream)
        # add logging config to be used by controllers and apps
        config['logger'] = logger

    # import controllers
    for controller in config['controllers']:
        # import the module
        logger.debug("Loading controller " + controller + "...")
        module = importlib.import_module(config['controllers'][controller]['module'])
        model['controllers'][controller] = module

    # Open and read the topology file for the real network
    with open(config['topology']['file'], 'r') as stream:
        # Load the YAML topology file
        clab_topology_definition = yaml.safe_load(stream)
        if clab_topology_definition.get('prefix'):
            config['clab_topology_prefix'] = clab_topology_definition['prefix']
        else:
            config['clab_topology_prefix'] = "clab"

    # create nodes in the real network model
    for node in clab_topology_definition['topology']['nodes'].items():
        model['nodes'][node[0]] = dict()

    # Deploy the topology using Containerlab
    os.system(f"clab deploy {reconfigureContainers} -t {config['topology']['file']}")

    # Iterate over the siblings in the config
    for sibling in config['siblings']:
        # Create a sibling in the model
        model['siblings'][sibling] = dict()
        # create queue for the sibling
        model['queues'][sibling] = Queue()

        # Get the topology for the sibling
        sibling_clab_topo = copy.deepcopy(clab_topology_definition)
        # Update the name in the topology to reflect the sibling
        sibling_clab_topo['name'] = clab_topology_definition['name'] + "_" + sibling
        # Topology adjustments for the sibling
        if config['siblings'][sibling] is not None and config['siblings'][sibling].get('topology-adjustments'):
            for adjustment in config['siblings'][sibling]['topology-adjustments']:
                if adjustment == 'node-remove':
                    # Remove nodes from the topology
                    for node in sibling_clab_topo['topology']['nodes'].copy().items():
                        if re.fullmatch(config['siblings'][sibling]['topology-adjustments']['node-remove'], node[0]):
                            sibling_clab_topo['topology']['nodes'].pop(node[0])

                            # Remove links to removed nodes from the topology
                            for link in sibling_clab_topo['topology']['links']:
                                if any(endpoint.startswith(node[0] + ":") for endpoint in link['endpoints']):
                                    sibling_clab_topo['topology']['links'].pop(sibling_clab_topo['topology']['links'].index(link))
                if adjustment == 'node-add':
                    # Add nodes to the topology
                    for node in config['siblings'][sibling]['topology-adjustments']['node-add']:
                        node_config = config['siblings'][sibling]['topology-adjustments']['node-add'][node]
                        sibling_clab_topo['topology']['nodes'][node] = node_config
                if adjustment == 'link-remove':
                    # Remove links from the topology
                    for link in config['siblings'][sibling]['topology-adjustments']['link-remove']:
                        sibling_clab_topo['topology']['links'].pop(sibling_clab_topo['topology']['links'].index(link))
                if adjustment == 'link-add':
                    # Add links to the topology
                    for link in config['siblings'][sibling]['topology-adjustments']['link-add']:
                        sibling_clab_topo['topology']['links'].append(link)
        # Write the sibling topology to a new file
        with open("./" + config['name'] + "_sib_" + sibling + ".clab.yml", 'w') as stream:
            yaml.dump(sibling_clab_topo, stream)
        # Set the sibling topology in the model
        model['siblings'][sibling]['clab_topology'] = sibling_clab_topo

        sibling_config = config['siblings'].get(sibling)
        # If the sibling config exists and autostart is enabled
        if sibling_config:
            if sibling_config.get('autostart'):
                # Deploy the sibling topology using Containerlab
                logger.info("Deploying sibling " + sibling + "...")
                os.system(f"clab deploy {reconfigureContainers} -t {config['name']}_sib_{sibling}.clab.yml")
                model['siblings'][sibling]['running'] = True

    # start controllers for siblings
    for sibling in model['siblings']:
        if model['siblings'][sibling].get('running'):
            # if sibling has a controller defined, start it
            if config['siblings'][sibling].get('controller'):
                logger.info("=== Start Controller for " + sibling + "...")
                configured_sibling_controller = config['siblings'][sibling]['controller']
                controller_instance = getattr(model['controllers'][configured_sibling_controller], configured_sibling_controller)
                model['siblings'][sibling]['controller'] = controller_instance(config, clab_topology_definition, model, sibling)

    # main loop (sync network state between real net and siblings)
    logger.info("Starting main loop...")
    while True:
        logger.debug("sleeping until next sync interval...")
        time.sleep(config['interval'])

        # get gNMI data from the real network
        # could be improved by using subscribe instead of get
        logger.debug("<-- Getting gNMI data from the real network...")

        # save old model for comparison until we implement subscriptions etc.
        old_model = dict()
        old_model['nodes'] = copy.deepcopy(model['nodes'])

        port = config['gnmi']['port']
        username = config['gnmi']['username']
        password = config['gnmi']['password']
        for node in clab_topology_definition['topology']['nodes'].items():
            if re.fullmatch(config['gnmi']['nodes'], node[0]):
                host = config['clab_topology_prefix'] + "-" + clab_topology_definition['name'] + "-" + node[0]
                with gNMIclient(target=(host, port), username=username, password=password, insecure=True) as gc:
                    for path in config['gnmi']['paths']:
                        result = gc.get(path=[path], datatype=config['gnmi']['datatype'])
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

        # get further traffic data / network state etc.


if __name__ == '__main__':
    main()