from apps.app import Application

from datetime import datetime
import re
from pygnmi.client import gNMIclient


class hello_world(Application):
    '''Hello World app'''


    def __init__(self):
        '''Constructor'''
        super().__init__()


    async def run(self, config, real_topo, sibling_topo, queues, task):
        '''Run the hello-world app'''
        port = config['gnmi']['port']
        username = config['gnmi']['username']
        password = config['gnmi']['password']

        logger = config['logger']

        real_nodes = real_topo['nodes']

        sibling = sibling_topo['name']
        sib_nodes = sibling_topo['nodes']

        # if the sibling is not running, don't run the hello-world app
        if sibling_topo['running'] is False:
            logger.debug("hello-world app not running for sibling " + sibling + " because the sibling is not running")
            return

        logger.debug("Running hello-world app for sibling " + sibling + "...")

        if task is not None:
            logger.debug("hello-world app got Task: " + str(task) + ", ignoring it as hello-world does not react on tasks...")

        # for each node in the sibling's topology, set the description of Ethernet1 to "Hello World!" and a timestamp using gNMI
        if len(sib_nodes) > 0:
            for node in sib_nodes.items():
                node_name = node[0]
                # if the sibling has a gnmi-sync config and the node matches the regex
                if config['siblings'][sibling].get('gnmi-sync') is not None and config['siblings'][sibling]['gnmi-sync'].get('nodes'):
                    if re.fullmatch(config['siblings'][sibling]['gnmi-sync']['nodes'], node[0]):
                        # if the node's name also exists in real_nodes (e.g., not the case for a node that was added to the sibling's topology)
                        if real_nodes.get(node[0]) is not None:
                            host = config['clab_topology_prefix'] + "-" + config['clab_topology_name'] + "_" + sibling + "-" + node[0]
                            try:
                                with gNMIclient(target=(host, port), username=username, password=password, insecure=True) as gc:
                                    test_message = "Hello World! for node " + node[0] + " in sibling " + sibling + " at " + datetime.now().strftime("%H:%M:%S")
                                    logger.debug("Setting interface description for Ethernet1 on node " + node[0] + " in sibling " + sibling + " to: " + test_message)
                                    try:
                                        sib_nodes[node_name]['gNMIWriteSemaphore'].acquire()
                                        result = gc.set(update=[("openconfig:interfaces/interface[name=Ethernet1]", {"config": {"description": test_message}})])
                                        sib_nodes[node_name]['gNMIWriteSemaphore'].acquire()
                                        logger.debug(result)
                                    except Exception as e:
                                        logger.error("Error setting interface desc for Ethernet1 on " + host + " in sibling " + sibling + ": " + str(e))
                            except:
                                logger.error("Error connecting to " + host + " in sibling " + sibling)