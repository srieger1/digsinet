#!/usr/bin/env python3
import argparse
import asyncio
import os
import signal
import sys
import time
import importlib
import logging

import yaml

from multiprocessing import Queue

logger = None


def gracefull_shutdown_handler(sig, frame):
    print("Shutting down gracefully...")
    # handle gRPC and gNMI connection loss messages etc.
    sys.exit(0)


def main():
    global logger

    signal.signal(signal.SIGINT, gracefull_shutdown_handler)

    # Create an argument parser
    parser = argparse.ArgumentParser()

    action_group = parser.add_mutually_exclusive_group()
    action_group.add_argument('--start', help='Start DigSiNet, create sibling topologies and run controllers, apps and'
                              ' interfaces.',
                              action='store_true', default=True)
    action_group.add_argument('--stop', help='Stop and remove DigSiNet sibling topologies.', action='store_true',
                              default=False)
    action_group.add_argument('--cleanup', help='Forcefully cleanup all sibling topologies.', action='store_true',
                              default=False)
    parser.add_argument('--yes-i-really-mean-it', help='Confirm forcefull cleanup', action='store_true', default=False)

    parser.add_argument('--config', help='Config file', default='./digsinet.yml')
    parser.add_argument('--reconfigure', help='Reconfigure existing containerlab containers', action='store_true')
    parser.add_argument('--debug', help='Enable debug logging', action='store_true')
    parser.add_argument('--task-debug', help='Enable task debug logging', action='store_true')
    args = parser.parse_args()

    # If the reconfigure flag is set, clab will be told to reconfigure existing containers
    reconfigureContainers = "--reconfigure" if args.reconfigure else ""

    logger = logging.getLogger(__name__)
    # If the debug flag is set, the log level will be set to debug
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logging.basicConfig(level=logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler())

    config = load_config(args.config, args)
    # Add config flags
    config['reconfigureContainers'] = reconfigureContainers

    if args.cleanup:
        if args.yes_i_really_mean_it:
            os.system("clab destroy -a -c")
        else:
            print("Please confirm forcefull cleanup by using the --yes-i-really-mean-it flag")
            exit(1)
    elif args.stop:
        os.system(f"clab destroy -t {config['topology']['file']}")

        for sibling in config['siblings']:
            sibling_config = config['siblings'].get(sibling)
            if sibling_config:
                if sibling_config.get('autostart'):
                    os.system(f"clab destroy -t {config['name']}_sib_{sibling}.clab.yml")
    elif args.start:
        controllers = load_controllers(config)
        realnet_apps = load_realnet_apps(config)
        realnet_interfaces = load_realnet_interfaces(config)
        clab_topology_definition = load_topology(config)

        nodes = create_nodes(clab_topology_definition)
        deploy_topology(reconfigureContainers, config)

        queues = create_queues(config['siblings'])
        siblings = create_siblings(config['siblings'], controllers, config, clab_topology_definition, nodes, queues)

        main_loop(config, realnet_interfaces, realnet_apps, siblings, nodes, queues)


def load_config(config_file, args):
    with open(config_file, 'r') as stream:
        config = yaml.safe_load(stream)
        config['logger'] = logger
        # If the task debug flag is set, all tasks will be logged
        config['task-debug'] = args.task_debug
    return config


def load_controllers(config):
    controllers = {}
    for controller in config['controllers']:
        logger.debug(f"Loading controller {controller}...")
        module = importlib.import_module(config['controllers'][controller]['module'])
        controllers[controller] = module
    return controllers


def load_realnet_apps(config):
    realnet_apps = {}
    if config['realnet'].get('apps'):
        for app in config['realnet']['apps']:
            logger.debug(f"Loading app {app}...")
            module = importlib.import_module(config['apps'][app]['module'])
            app_class = getattr(module, app)
            app_instance = app_class(config)
            realnet_apps[app] = app_instance
    return realnet_apps


def load_realnet_interfaces(config):
    realnet_interfaces = {}
    for interface in config['realnet']['interfaces']:
        logger.debug(f"Loading interface {interface}...")
        module = importlib.import_module(config['interfaces'][interface]['module'])
        interface_class = getattr(module, interface)
        interface_instance = interface_class(config, 'realnet')
        realnet_interfaces[interface] = interface_instance
    return realnet_interfaces


def load_topology(config):
    with open(config['topology']['file'], 'r') as stream:
        clab_topology_definition = yaml.safe_load(stream)
        if clab_topology_definition.get('prefix'):
            config['clab_topology_prefix'] = clab_topology_definition['prefix']
        else:
            config['clab_topology_prefix'] = "clab"
        config['clab_topology_name'] = clab_topology_definition.get('name')
    return clab_topology_definition


def create_nodes(clab_topology_definition):
    nodes = dict()
    for node in clab_topology_definition['topology']['nodes'].items():
        nodes[node[0]] = dict()
    return nodes


def deploy_topology(reconfigureContainers, config):
    os.system(f"clab deploy {reconfigureContainers} -t {config['topology']['file']}")


def create_queues(siblings):
    queues = dict()
    queues['realnet'] = Queue()
    for sibling in siblings:
        queues[sibling] = Queue()
    return queues


def create_siblings(siblings_config, controllers, config, clab_topology_definition, nodes, queues):
    siblings = dict()
    for sibling in siblings_config:
        siblings[sibling] = dict()
        if siblings_config[sibling].get('controller'):
            logger.info(f"=== Start Controller for {sibling}...")
            configured_sibling_controller = siblings_config[sibling]['controller']
            controller_class = getattr(controllers[configured_sibling_controller], configured_sibling_controller)
            controller_instance = controller_class(config, clab_topology_definition, nodes, sibling, queues)
            siblings[sibling]['controller'] = controller_instance
            logger.info(f"=== Build sibling {sibling} using its controller...")
            queues[sibling].put({"type": "topology build request",
                                 "source": "realnet",
                                 "sibling": sibling})
            timeout = config['create_sibling_timeout']
            while timeout > 0:
                if not queues["realnet"].empty():
                    task = queues["realnet"].get(timeout=5)
                    if task['type'] == "topology build response" and task["sibling"] == sibling:
                        siblings[sibling].update({"topology": task['topology'],
                                                  "nodes": task['nodes'],
                                                  "interfaces": task['interfaces'],
                                                  "running": task['running']})
                        # print(" done")
                        break
                    else:
                        # print("+", end="")
                        time.sleep(.1)
                        timeout -= .1
                else:
                    # print("*", end="")
                    time.sleep(.1)
                    timeout -= .1
            if timeout == 0:
                logger.error(f"Timeout while waiting for topology build response for sibling {sibling}")
                exit(1)
    return siblings


def main_loop(config, realnet_interfaces, realnet_apps, siblings, nodes, queues):
    logger.info("=== Entering main Loop...")
    stats_interval = 10
    while True:
        time.sleep(config['interval'])
        stats_interval -= 1
        if stats_interval == 0:
            stats_interval = 10
            queue_stats = ""
            for queue in queues:
                queue_stats += f" ({queue}, size: {str(queues[queue].qsize())})"
            logger.info(f"=== Queue stats: {queue_stats}")
        for interface in realnet_interfaces:
            interface_instance = realnet_interfaces[interface]
            nodes = interface_instance.getNodesUpdate(nodes, queues, diff=True)
        realnet_queue = queues["realnet"]
        task = None
        if not queues["realnet"].empty():
            # process the tasks for realnet batch-wise based on the queue size
            for _ in range(realnet_queue.qsize()):
                task = realnet_queue.get()
                if config['task-debug']:
                    logger.info(f"*** Realnet got task: {str(task)}")
                if task['type'] == "topology build response":
                    sibling = task['sibling']
                    siblings[sibling].update({"topology": task['topology'],
                                              "nodes": task['nodes'],
                                              "interfaces": task['interfaces'],
                                              "running": task['running']})
                for app in realnet_apps:
                    logger.debug(f"=== Running App {app[0]} on realnet...")
                    asyncio.run(app[1].run(config, siblings[task['sibling']], queues, task))
                # queues["realnet"].task_done()


if __name__ == '__main__':
    main()
