#!/usr/local/bin/python3
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

    # Create the information model
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
        config['reconfigureContainers'] = reconfigureContainers

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

    # create nodes for the real network model
    for node in clab_topology_definition['topology']['nodes'].items():
        model['nodes'][node[0]] = dict()

    # Deploy the topology using Containerlab
    os.system(f"clab deploy {reconfigureContainers} -t {config['topology']['file']}")

    # add a queue for the real network
    model['queues']['realnet'] = Queue()

    # Iterate over the siblings in the config to create them and start their controllers
    for sibling in config['siblings']:
        # Create a sibling in the model
        model['siblings'][sibling] = dict()
        # create queue for the sibling
        model['queues'][sibling] = Queue()

        # Build and potentially start the sibling using its assigned controller
        if config['siblings'][sibling].get('controller'):
            logger.info("=== Start Controller for " + sibling + "...")
            configured_sibling_controller = config['siblings'][sibling]['controller']
            controller_class = getattr(model['controllers'][configured_sibling_controller], configured_sibling_controller)
            controller_instance = controller_class(config, clab_topology_definition, sibling, model['nodes'], model['queues'])
            model['siblings'][sibling]['controller'] = controller_instance

            logger.info("=== Build sibling " + sibling + " using its controller...")
            # add sibling topology and running config to the model
            sibling_topo_state = controller_instance.build_sibling(config, clab_topology_definition)
            model['siblings'][sibling].update(sibling_topo_state)


    # main loop (sync network state between real net and siblings)
    logger.info("Starting main loop...")
    while True:
        logger.debug("sleeping until next sync interval...")
        time.sleep(config['interval'])

        # get gNMI data from the real network
        # could be improved by using subscribe instead of get
        logger.debug("<-- Getting gNMI data from the real network...")

        # save old model for comparison until we implement subscriptions etc.
        old_nodes = copy.deepcopy(model['nodes'])

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
                        diff = DeepDiff(old_nodes, model['nodes'], ignore_order=True, exclude_regex_paths="\\['timestamp'\\]")

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