#!/usr/bin/python3
import argparse
import os
import time
import yaml
from pygnmi.client import gNMIclient
import copy
import importlib
import asyncio

def main():
    # Create an argument parser
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', help='Config file', default='./digsinet.yml')
    parser.add_argument('--reconfigure', help='Reconfigure existing containerlab containers', action='store_true')
    args = parser.parse_args()

    # If the reconfigure flag is set, set the reconfigureContainers variable
    if args.reconfigure:
        reconfigureContainers = "--reconfigure"
    else:
        reconfigureContainers = ""

    # Create information model for the real network
    model = dict()
    model['nodes'] = dict()
    model['siblings'] = dict()
    model['apps'] = dict()

    # Open and read the config file
    with open(args.config, 'r') as stream:
        # Load the YAML config file
        config = yaml.safe_load(stream)

    # load apps
    for app in config['apps']:
        # load the module
        print("Loading app " + app + "...")
        model['apps'][app] = importlib.import_module(config['apps'][app]['module'])
        # load the module
        # model['apps'][app].load(config['apps'][app], model)

    # Open and read the topology file for the real network
    with open(config['topology']['file'], 'r') as stream:
        # Load the YAML topology file
        clab_topology_definition = yaml.safe_load(stream)

    # create nodes in the real network model
    for node in clab_topology_definition['topology']['nodes'].items():
        model['nodes'][node[0]] = dict()

    # Deploy the topology using Containerlab
    os.system(f"clab deploy {reconfigureContainers} -t {config['topology']['file']}")

    # Iterate over the siblings in the config
    for sibling in config['siblings']:
        # Create a sibling in the real network model
        model['siblings'][sibling] = dict()

        # Get the topology for the sibling
        sibling_clab_topo = copy.deepcopy(clab_topology_definition)
        # Update the name in the topology to reflect the sibling
        sibling_clab_topo['name'] = clab_topology_definition['name'] + "_" + sibling
        # Write the sibling topology to a new file
        with open("./" + config['name'] + "_sib_" + sibling + ".clab.yml", 'w') as stream:
            yaml.dump(sibling_clab_topo, stream)

        sibling_config = config['siblings'].get(sibling)
        # If the sibling config exists and autostart is enabled
        if sibling_config:
            if sibling_config.get('autostart'):
                # Deploy the sibling topology using Containerlab
                os.system(f"clab deploy {reconfigureContainers} -t {config['name']}_sib_{sibling}.clab.yml")
                model['siblings'][sibling]['running'] = True

    # main loop
    while True:
        time.sleep(config['interval'])

        # could be improved by using subscribe instead of get

        # get gNMI data from the real network
        print("<-- Getting gNMI data from the real network...")
        port = config['gnmi']['port']
        username = config['gnmi']['username']
        password = config['gnmi']['password']
        for node in clab_topology_definition['topology']['nodes'].items():
            host = "clab-" + clab_topology_definition['name'] + "-" + node[0]
            # assume clab as the default prefix for now
            with gNMIclient(target=(host, port), username=username, password=password, insecure=True) as gc:
                for path in config['gnmi']['paths']:
                    result = gc.get(path=[path], datatype=config['gnmi']['datatype'])
                    # for strip in config['gnmi']['strip']:
                    #    # result = result.pop(strip)
                    model['nodes'][node[0]][path] = copy.deepcopy(result)

        # get and set traffic data / network state etc.

        # run controller apps
        for sibling in model['siblings']:
            if model['siblings'][sibling].get('running'):
                print("=== Run Controller for " + sibling + "...")
                # get controller for sibling and its apps and run them
                for app in config['controllers'][config['siblings'][sibling]['controller']]['apps']:
                    # parallelized execution is suboptimal for now
                    asyncio.run(model['apps'][app].run(config, clab_topology_definition, model, sibling))
                    # model['apps'][app].run(config, clab_topology_definition, model, sibling)

        # setting gNMI data on running siblings, could be improved to only run on changed data
        for sibling in model['siblings']:
            if model['siblings'][sibling].get('running'):
                print("--> Setting gNMI data on sibling " + sibling + "...")
                # assume same nodes in each sibling as in real network for now
                for node in clab_topology_definition['topology']['nodes'].items():
                    # assume clab as the default prefix for now
                    host = "clab-" + clab_topology_definition['name'] + "_" + sibling + "-" + node[0]
                    with gNMIclient(target=(host, port), username=username, password=password, insecure=True) as gc:
                        for path in model['nodes'][node[0]]:
                            for notification in model['nodes'][node[0]][path]['notification']:
                                for update in notification['update']:
                                    result = gc.set(update=[(str(path), dict(update['val']))])

        print("sleeping...")

if __name__ == '__main__':
    main()