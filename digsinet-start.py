#!/usr/bin/python3
import argparse
import os
import time
import yaml
from pygnmi.client import gNMIclient
import copy
import importlib
import re

from controllers.controller import Controller

def main():
    # Create an argument parser
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', help='Config file', default='./digsinet.yml')
    parser.add_argument('--reconfigure', help='Reconfigure existing containerlab containers', action='store_true')
    args = parser.parse_args()

    # If the reconfigure flag is set, clab will be told to reconfigure existing containers
    if args.reconfigure:
        reconfigureContainers = "--reconfigure"
    else:
        reconfigureContainers = ""

    # Create information model for the real network
    model = dict()
    model['nodes'] = dict()
    model['siblings'] = dict()
    model['controllers'] = dict[Controller]()

    # Open and read the config file
    with open(args.config, 'r') as stream:
        # Load the YAML config file
        config = yaml.safe_load(stream)

    # import controllers
    for controller in config['controllers']:
        # import the module
        print("Loading controller " + controller + "...")
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
                os.system(f"clab deploy {reconfigureContainers} -t {config['name']}_sib_{sibling}.clab.yml")
                model['siblings'][sibling]['running'] = True

    # start controllers for siblings
    for sibling in model['siblings']:
        if model['siblings'][sibling].get('running'):
            # get controller for sibling and start it
            print("=== Run Controller for " + sibling + "...")
            # if sibling has a controller defined, start it
            if config['siblings'][sibling].get('controller'):
                configured_sibling_controller = config['siblings'][sibling]['controller']
                controller_instance = getattr(model['controllers'][configured_sibling_controller], configured_sibling_controller)
                model['siblings'][sibling]['controller'] = controller_instance(config, clab_topology_definition, model, sibling)

    # main loop (sync network state between real net and siblings)
    while True:
        print("sleeping until next sync interval...")
        time.sleep(config['interval'])

        # get gNMI data from the real network
        # could be improved by using subscribe instead of get
        print("<-- Getting gNMI data from the real network...")
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

        # get traffic data / network state etc.

    	# run apps for siblings
        for sibling in model['siblings']:
            if model['siblings'][sibling].get('running'):
                # get controller for sibling and run apps
                # print("=== Run Apps on Controller for " + sibling + "...")
                # if sibling has a controller defined, run its apps
                if model['siblings'][sibling].get('controller'):
                    # get runApps as a callable method and call it
                    runApps = controller_instance = getattr(model['siblings'][sibling]['controller'], 'runApps')
                    runApps()

        # setting gNMI data on nodes for running siblings
        # TODO: could be improved to only run on changed data
        for sibling in model['siblings']:
            # if the sibling is running
            if model['siblings'][sibling].get('running'):
                for node in model['siblings'][sibling]['clab_topology']['topology']['nodes'].items():
                    # if the sibling has a gnmi-sync config and the node matches the regex
                    if config['siblings'][sibling].get('gnmi-sync') is not None and config['siblings'][sibling]['gnmi-sync'].get('nodes'):
                        if re.fullmatch(config['siblings'][sibling]['gnmi-sync']['nodes'], node[0]):
                            # if the gNMI data for the node's name exists in the model (e.g., not the case for a node that was added to the sibling's topology)
                            if model['nodes'].get(node[0]) is not None:
                                print("--> Setting gNMI data on node " + node[0] + " in sibling " + sibling + "...")
                                host = config['clab_topology_prefix'] + "-" + clab_topology_definition['name'] + "_" + sibling + "-" + node[0]
                                with gNMIclient(target=(host, port), username=username, password=password, insecure=True) as gc:
                                    # for each path in the model for the node
                                    for path in model['nodes'][node[0]]:
                                        for notification in model['nodes'][node[0]][path]['notification']:
                                            # if the notification is an update
                                            if notification.get('update'):
                                                for update in notification['update']:
                                                    result = gc.set(update=[(str(path), dict(update['val']))])

if __name__ == '__main__':
    main()