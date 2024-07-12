#!/usr/bin/env python3
import argparse
import asyncio
import json
import os
import signal
import sys
import time
import importlib
import logging
from event.kafka import KafkaClient

import yaml

from config import ArgParser, read_config
from interfaces.interface import Interface

logger = None
broker = None


def gracefull_shutdown_handler(sig, frame):
    global broker
    print("Shutting down gracefully...")
    if broker:
        broker.close()
    # handle gRPC and gNMI connection loss messages etc.
    sys.exit(0)


def main():
    global logger, broker

    signal.signal(signal.SIGINT, gracefull_shutdown_handler)

    # Create an argument parser
    parser = ArgParser()
    args = parser.get_args()

    # If the reconfigure flag is set, clab will be told to reconfigure existing containers
    reconfigure_containers = "--reconfigure" if args.reconfigure else ""

    logger = logging.getLogger(__name__)
    # If the debug flag is set, the log level will be set to debug
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logging.basicConfig(level=logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler())

    config = read_config(args.config)
    # Add config flags
    # config['reconfigure_containers'] = reconfigure_containers

    if args.cleanup:
        if args.yes_i_really_mean_it:
            os.system("clab destroy -a -c")
        else:
            print(
                "Please confirm forcefull cleanup by using the --yes-i-really-mean-it flag"
            )
            exit(1)
    elif args.stop:
        os.system(f"clab destroy -t {config.topology.file}")

        for sibling in config.siblings:
            sibling_config = config.siblings.get(sibling)
            if sibling_config:
                if sibling_config.autostart:
                    os.system(
                        f"clab destroy -t {config.topology_name}_sib_{sibling}.clab.yml"
                    )
    elif args.start:
        clab_topology_definition = load_topology(config)
        topology_name = clab_topology_definition.get("name")
        topology_prefix = "clab"
        controllers = load_controllers(config)
        realnet_apps = load_realnet_apps(config)
        realnet_interfaces = load_realnet_interfaces(
            config, topology_name, topology_prefix
        )

        nodes = create_nodes(clab_topology_definition)
        deploy_topology(reconfigure_containers, config)

        broker = create_queues(config.siblings, config.kafka)

        siblings = create_siblings(
            config.siblings,
            controllers,
            config,
            clab_topology_definition,
            nodes,
            broker,
            reconfigure_containers,
            topology_name,
            topology_prefix,
        )

        main_loop(config, realnet_interfaces, realnet_apps, siblings, nodes, broker)


def load_controllers(config):
    controllers = {}
    for controller in config.controllers:
        logger.debug(f"Loading controller {controller}...")
        module = importlib.import_module(config.controllers.get(controller).module)
        controllers[controller] = module
    return controllers


def load_realnet_apps(config):
    realnet_apps = {}
    if config.realnet.apps is not None:
        for app in config.realnet.apps:
            logger.debug(f"Loading app {app}...")
            module = importlib.import_module(config.apps.get(app).module)
            app_class = getattr(module, app)
            app_instance = app_class(config, logger)
            realnet_apps[app] = app_instance
    return realnet_apps


def load_realnet_interfaces(config, topology_name, topology_prefix):
    realnet_interfaces = {}
    for interface in config.realnet.interfaces:
        logger.debug(f"Loading interface {interface}...")
        module = importlib.import_module(
            config.interface_credentials.get(interface).module
        )
        interface_class = getattr(module, interface)
        interface_instance = interface_class(
            config, "realnet", logger, topology_prefix, topology_name
        )
        realnet_interfaces[interface] = interface_instance
    return realnet_interfaces


def load_topology(config):
    with open(config.topology.file, "r") as stream:
        clab_topology_definition = yaml.safe_load(stream)
        return clab_topology_definition


def create_nodes(clab_topology_definition):
    nodes = dict()
    for node in clab_topology_definition["topology"]["nodes"].items():
        nodes[node[0]] = dict()
    return nodes


def deploy_topology(reconfigureContainers, config):
    os.system(f"clab deploy {reconfigureContainers} -t {config.topology.file}")


def create_queues(siblings, stream_config):
    queue_names = []
    for sibling in siblings:
        queue_names.append(sibling)
    queue_names.append("realnet")
    client = KafkaClient(stream_config, queue_names, logger)
    return client


def create_siblings(
    siblings_config,
    controllers,
    config,
    clab_topology_definition,
    nodes,
    kafka_client: KafkaClient,
    reconfigure_containers,
    topology_name,
    topology_prefix,
):
    siblings = dict()
    consumer, key = kafka_client.subscribe("realnet", "create_siblings")
    for sibling in siblings_config:
        siblings[sibling] = dict()
        if siblings_config[sibling].controller:
            logger.info(f"=== Start Controller for {sibling}...")
            configured_sibling_controller = siblings_config[sibling].controller
            controller_class = getattr(
                controllers[configured_sibling_controller],
                configured_sibling_controller,
            )
            controller_instance = controller_class(
                config,
                clab_topology_definition,
                nodes,
                sibling,
                kafka_client,
                logger,
                reconfigure_containers,
                topology_prefix,
                topology_name,
            )
            siblings[sibling]["controller"] = controller_instance
            logger.info(f"=== Build sibling {sibling} using its controller...")
            kafka_client.publish(
                sibling,
                {
                    "type": "topology build request",
                    "source": "realnet",
                    "sibling": sibling,
                },
            )
            timeout = config.sibling_timeout
            try:
                logger.info(f"Waiting for topology build response for realnet...")
                while True:
                    message = kafka_client.poll(consumer, timeout=timeout)
                    if message is None:
                        logger.error(
                            f"Timeout while waiting for topology build response from sibling {sibling}"
                        )

                        kafka_client.close()
                        exit(1)
                    elif message.error():
                        logger.error(f"Consumer error: {message.error()}")
                        kafka_client.close()
                        exit(1)
                    else:
                        task = json.loads(message.value())

                        if (
                            task["type"] == "topology build response"
                            and task["sibling"] == sibling
                        ):
                            siblings[sibling].update(
                                {
                                    "topology": task["topology"],
                                    "nodes": task["nodes"],
                                    "interfaces": task["interfaces"],
                                    "running": task["running"],
                                }
                            )
                            break
            finally:
                logger.debug(f"Topology build response for sibling {sibling} received.")

    logger.debug(f"Closing consumer...")
    kafka_client.closeConsumer(key)
    return siblings


def main_loop(
    config, realnet_interfaces, realnet_apps, siblings, nodes, kafka_client: KafkaClient
):
    logger.info("=== Entering main Loop...")
    # stats_interval = 10
    consumer, key = kafka_client.subscribe("realnet", "main_loop")
    try:
        while True:
            # Stats removed for now - will be used in dashboard
            # Not required with new event stream design

            # stats_interval -= 1
            # if stats_interval == 0:
            #     stats_interval = 10
            #     queue_stats = ""
            #     # TODO Replace queues
            #     # for queue in queues:
            #     #     queue_stats += f" ({queue}, size: {str(queues[queue].qsize())})"
            #     logger.info(f"=== Queue stats: {queue_stats}")
            for interface in realnet_interfaces:
                interface_instance: Interface = realnet_interfaces[interface]
                logger.info(
                    f"=== Pass Siblings {siblings} to interface {interface} for getNodesUpdate..."
                )
                nodes = interface_instance.getNodesUpdate(
                    nodes, siblings, kafka_client, diff=True
                )
            task = None
            logger.info(f"Checking for consumer message in main loop for realnet...")
            message = kafka_client.poll(consumer, config.sync_interval)
            if message is None:
                logger.error(f"Timeout while waiting for task for realnet")
                # kafka_client.close()
                # exit(1)
            elif message.error():
                logger.error(f"Consumer error: {message.error()}")
                kafka_client.close()
                exit(1)
            else:
                task = json.loads(message.value())
                logger.info(f"Got task {task}...")
                logger.debug(f"*** Realnet got task: {str(task)}")
                if task["type"] == "topology build response":
                    sibling = task["sibling"]
                    siblings[sibling].update(
                        {
                            "topology": task["topology"],
                            "nodes": task["nodes"],
                            "interfaces": task["interfaces"],
                            "running": task["running"],
                        }
                    )
                for app in realnet_apps:
                    logger.debug(f"=== Running App {app[0]} on realnet...")
                    asyncio.run(
                        app[1].run(
                            config, siblings[task["sibling"]], kafka_client, task
                        )
                    )
                # queues["realnet"].task_done()
    finally:
        kafka_client.closeConsumer(key)


if __name__ == "__main__":
    main()
