#!/usr/bin/env python3
import argparse
import asyncio
import os
import time
import importlib
import logging

import yaml

from controllers.controller import Controller
from apps.app import Application
from interfaces.interface import Interface
from multiprocessing import Queue


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

    # Create the information model for realnet
    nodes = dict()
    siblings = dict()
    controllers = dict[Controller]()
    realnet_apps = dict[Application]()
    realnet_interfaces = dict[Interface]()
    queues = dict[Queue]()

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
        controllers[controller] = module

    # import apps configured for the real network
    if config['realnet'].get('apps'):
        for app in config['realnet']['apps']:
            # import the module
            logger.debug("Loading app " + app + "...")
            module = importlib.import_module(config['apps'][app]['module'])
            app_class = getattr(module, app)
            app_instance = app_class(config)
            realnet_apps[app] = app_instance

    # import interfaces configured for the real network
    for interface in config['realnet']['interfaces']:
        # import the module
        logger.debug("Loading interface " + interface + "...")
        module = importlib.import_module(config['interfaces'][interface]['module'])
        interface_class = getattr(module, interface)
        interface_instance = interface_class(config, 'realnet')
        realnet_interfaces[interface] = interface_instance

    # Open and read the topology file for the real network
    with open(config['topology']['file'], 'r') as stream:
        # Load the YAML topology file
        clab_topology_definition = yaml.safe_load(stream)
        if clab_topology_definition.get('prefix'):
            config['clab_topology_prefix'] = clab_topology_definition['prefix']
        else:
            config['clab_topology_prefix'] = "clab"
        config['clab_topology_name'] = clab_topology_definition.get('name')

    # create nodes for the real network model
    for node in clab_topology_definition['topology']['nodes'].items():
        nodes[node[0]] = dict()

    # Deploy the topology using Containerlab
    os.system(f"clab deploy {reconfigureContainers} -t {config['topology']['file']}")

    # add a queue for the real network
    queues['realnet'] = Queue()
    # add model and queues for all siblings, to be used by the controllers
    for sibling in config['siblings']:
        # Create a sibling in the model
        siblings[sibling] = dict()
        queues[sibling] = Queue()

    # Iterate over the siblings in the config to create them and start their controllers
    for sibling in config['siblings']:
        # Build and potentially start the sibling using its assigned controller
        if config['siblings'][sibling].get('controller'):
            logger.info("=== Start Controller for " + sibling + "...")
            configured_sibling_controller = config['siblings'][sibling]['controller']
            controller_class = getattr(controllers[configured_sibling_controller], configured_sibling_controller)
            controller_instance = controller_class(config, clab_topology_definition, nodes, sibling, queues)
            siblings[sibling]['controller'] = controller_instance

            logger.info("=== Build sibling " + sibling + " using its controller...")
            # add sibling topology and running config to the model
            queues[sibling].put({"type": "topology build request",
                                 "source": "realnet",
                                 "sibling": sibling})
            # wait for topology build response
            while True:
                if not queues[sibling].empty():
                    task = queues["realnet"].get()
                    if task['type'] == "topology build response" and task["sibling"] ==sibling:
                        siblings[sibling].update({"topology": task['topology'],
                                                  "nodes": task['nodes'],
                                                  "interfaces": task['interfaces'],
                                                  "running": task['running']})
                        break
                else:
                    time.sleep(1)

    # main loop (sync network state between real net and siblings)
    logger.info("Starting main loop...")
    while True:
        logger.debug("sleeping until next sync interval...")
        time.sleep(config['interval'])

        for interface in realnet_interfaces:
            interface_instance = realnet_interfaces[interface]
            nodes = interface_instance.getNodeUpdateDiff(nodes, queues)

        logger.debug("Processing tasks and apps for realnet")
        realnet_queue = queues["realnet"]
        # get task from queue for realnet
        logger.debug("Checking queue for assigned realnet")
        task = None
        # if the queue is empty continue
        if not queues["realnet"].empty():
            task = realnet_queue.get()
            logger.debug("realnet got task " + str(task) + 
                         " approx queue size: " +
                         str(realnet_queue.qsize()))
            
            # process task
            if task['type'] == "topology build response":
                sibling = task['sibling']
                logger.debug("Processing topology build response for sibling " + sibling)
                # add sibling topology and running config to the model
                siblings[sibling].update({"topology": task['topology'],
                                            "nodes": task['nodes'],
                                            "interfaces": task['interfaces'],
                                            "running": task['running']})

        for app in realnet_apps:
            # parallelized execution is suboptimal for now
            logger.debug("=== Running App " + app[0] + " on realnet...")
            asyncio.run(app[1].run(config, siblings[task['sibling']], queues, task))
            # self.apps[app].run(self.config, self.siblings[sibling]['topology'], self.model, sibling, task)


        # get further traffic data / network state etc.


if __name__ == '__main__':
    main()