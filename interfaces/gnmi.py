'''gNMI interface'''
from multiprocessing import Semaphore
from interfaces.interface import Interface

import re
import copy

from pygnmi.client import gNMIclient

from deepdiff import DeepDiff, grep


class gnmi(Interface):
    '''
    gNMI interface
    '''

    port = None
    username = None
    password = None

    target = None

    config = dict()
    interface_config = dict()
    topology_interface_config = dict()

    hostWriteSemaphores = dict[Semaphore]()
    
    def __init__(self, config, target):
        '''
        Constructor
        '''
        super().__init__(config, target)

        self.port = config['interfaces']['gnmi']['port']
        self.username = config['interfaces']['gnmi']['username']
        self.password = config['interfaces']['gnmi']['password']

        self.target = target
        self.config = config

        if config["interfaces"] and config["interfaces"]["gnmi"]:
            self.interface_config = config["interfaces"]["gnmi"]

        self.topology_interface_config = super().getTopologyInterfaceConfig(target)

    def getHost(self, nodes, node_name):
        # if the gNMI data for the node's name exists in the model
        if len(nodes) > 0 and nodes.get(node_name) is not None:
            # if the topology has outgoing nodes defined
            if self.topology_interface_config.get('nodes'):
                # if the node matches the regex defined in the gnmi-sync config for the siblings
                if re.fullmatch(self.topology_interface_config['nodes'], node_name):
                    #TODO: hostname is still limited to containerlab syntax (clab_prefix-topology_name-node_name)
                    if self.target == "realnet":
                        host = self.config['clab_topology_prefix'] + "-" + self.config['clab_topology_name'] + "-" + node_name
                    else:
                        host = self.config['clab_topology_prefix'] + "-" + self.config['clab_topology_name'] + "_" + self.target + "-" + node_name

                    if self.hostWriteSemaphores.get(host) is None:
                        self.hostWriteSemaphores[host] = Semaphore(1)

                    #self.logger.info("Host for node " + node_name + " in topology " + self.target + " is " + host)

                    return host


    def getGNMI(self, nodes, queues, use_diff):
        # get gNMI data from the real network
        # could be improved by using subscribe instead of get
        self.logger.debug("<-- Getting differential gNMI data from " + self.target + "...")

        for node in nodes:
            host = self.getHost(nodes, node)
            # if the node is not in the topology or filtered by gNMI config, continue
            if host is None:
                continue

            try:
                with gNMIclient(target=(host, self.port), username=self.username, password=self.password, insecure=True) as gc:
                    for path in self.topology_interface_config['paths']:
                        if use_diff == True:
                            # save old node path data for comparison until we implement subscriptions etc.
                            if nodes[node].get(path) is not None:
                                old_node_path_data = copy.deepcopy(nodes[node][path])
                            else:
                                old_node_path_data = None

                        node_data = gc.get(path=[path], datatype=self.topology_interface_config['datatype'])
                        # for strip in config['gnmi']['strip']:
                        #    # result = result.pop(strip)
                        nodes[node][path] = copy.deepcopy(node_data)

                        diff = None
                        if use_diff == True:
                            # diff old and new nodes, excluding timestamp
                            exclude_timestamp = re.compile(r"\['timestamp'\]")
                            if node_data | grep("Hello World! update for node"):
                                #should be improved to detect changes by hello-world app 
                                #self.logger.info("gNMI silently ignoring 'Hello World' change notification in nodes from hello-world app...")
                                continue
                            #nodes_diff = DeepDiff(old_nodes, nodes, ignore_order=True, exclude_regex_paths="\\['timestamp'\\]")
                            node_data_diff = DeepDiff(old_node_path_data, node_data, ignore_order=True, exclude_regex_paths=[exclude_timestamp])

                            # if changes were detected, send an update to the controller queues
                            if node_data_diff.tree == {}:
                                continue
                            else:
                                diff = node_data_diff.tree
                                #self.logger.debug("gNMI diff detected change in " + self.target + ": " + str(diff))

                        for queue in queues:
                            queues[queue].put({"type": "gNMI notification", 
                                                        "source": self.target, 
                                                        "node": node, 
                                                        "path": path, 
                                                        "data": node_data,
                                                        "diff": diff})
            except Exception as e:
                self.logger.error("Error getting gNMI data from " + host + " in topology " + self.target + ": " + str(e))

        return nodes

    def getNodeUpdate(self, nodes, queues):
        return self.getGNMI(nodes, queues, False)

    def getNodeUpdateDiff(self, nodes, queues):
        return self.getGNMI(nodes, queues, True)

    def setNodeUpdate(self, nodes: dict, node_name: str, path: str, notification_data: dict):
        host = self.getHost(nodes, node_name)

        if host is not None:
            self.logger.debug("--> Syncing gNMI data to node " + node_name + " in topology " + self.target + ": " + str(notification_data) + "...")
            try:
                with gNMIclient(target=(host, self.port), username=self.username, password=self.password, insecure=True) as gc:
                    # for each notification in the notification data
                    for notification in notification_data['notification']:
                        # if the notification is an update
                        if notification.get('update'):
                            for update in notification['update']:
                                self.hostWriteSemaphores[host].acquire()
                                # turn update to replace, gygnmi get delivers updates, but updating, e.g., ip address in interface config 
                                # requires replacing it, otherwise we get gRPC errors
                                result = gc.set(replace=[(str(path), dict(update['val']))])
                                self.hostWriteSemaphores[host].release()
                                self.logger.debug("gNMI set result: " + str(result))
                        else:
                            self.logger.info("Unsupported gNMI notification type: " + str(notification))
            except Exception as e:
                self.logger.error("Error syncing gNMI data to " + host + " in topology " + self.target + ": " + str(e))

    def set(self, nodes: dict, node_name: str, op: str, data: dict):
        host = self.getHost(nodes, node_name)

        if host is not None:
            self.logger.debug("--> Setting gNMI data on node " + node_name + " in topology " + self.target + ": " + str(data) + "...")
            try:
                with gNMIclient(target=(host, self.port), username=self.username, password=self.password, insecure=True) as gc:
                    # for each notification in the notification data
                    self.hostWriteSemaphores[host].acquire()
                    match op:
                        case "update":
                            result = gc.set(update=data)
                        case "replace":
                            result = gc.set(replace=data)
                        case "delete":
                            result = gc.set(delete=data)
                        case _:
                            raise Exception("Unsupported gNMI operation: " + op)
                    self.hostWriteSemaphores[host].release()
                    self.logger.debug("gNMI set result: " + str(result))
            except Exception as e:
                self.logger.error("Error setting gNMI data on " + host + " in topology " + self.target + ": " + str(e))
