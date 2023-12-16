from datetime import datetime
import re
from pygnmi.client import gNMIclient

async def run(config, clab_topology_definition, model, sibling, task):
    port = config['gnmi']['port']
    username = config['gnmi']['username']
    password = config['gnmi']['password']

    logger = config['logger']

    logger.debug("Running hello-world app for sibling " + sibling + "...")

    if task is not None:
        logger.debug("hello-world app got Task: " + str(task))

    # for each node in the sibling's topology, set the description of Ethernet1 to "Hello World!" and a timestamp using gNMI
    for node in model['siblings'][sibling]['clab_topology']['topology']['nodes'].items():
        # if the sibling has a gnmi-sync config and the node matches the regex
        if config['siblings'][sibling].get('gnmi-sync') is not None and config['siblings'][sibling]['gnmi-sync'].get('nodes'):
            if re.fullmatch(config['siblings'][sibling]['gnmi-sync']['nodes'], node[0]):
                # if the gNMI data for the node's name exists in the model (e.g., not the case for a node that was added to the sibling's topology)
                if model['nodes'].get(node[0]) is not None:
                    host = config['clab_topology_prefix'] + "-" + clab_topology_definition['name'] + "_" + sibling + "-" + node[0]
                    try:
                        with gNMIclient(target=(host, port), username=username, password=password, insecure=True) as gc:
                            test_message = "Hello World! for node " + node[0] + " in sibling " + sibling + " at " + datetime.now().strftime("%H:%M:%S")
                            logger.debug("Setting interface description for Ethernet1 on node " + node[0] + " in sibling " + sibling + " to: " + test_message)
                            try:
                                result = gc.set(update=[("openconfig:interfaces/interface[name=Ethernet1]", {"config": {"description": test_message}})])
                                logger.debug(result)
                            except:
                                logger.error("Error setting interface desc for Ethernet1 on " + host + " in sibling " + sibling)
                    except:
                        logger.error("Error connecting to " + host + " in sibling " + sibling)