from controllers.controller import Controller

import asyncio

import copy
import re
import time

from pygnmi.client import gNMIclient

from deepdiff import DeepDiff

class ci(Controller):
    def __init__(self, config, real_topology_definition, real_nodes, queues):
        Controller.__init__(self, config, real_topology_definition, real_nodes, queues)


    def name(self):
        return "ci"


    def build_sibling(self, sibling, config, real_topology_definition):
        return super().build_sibling(sibling, config, real_topology_definition)


    def run(self):
        '''
        Start the controller with the applications for the assigned siblings.

        Checks the queue for the assigned sibling and runs the apps.

        If task is None (queue was empty), the controller runs the apps on a regular interval.
        If task is not None, the controller runs the apps on the task.
        Also, the task type is checked and if it is a gNMI notification and the source was the realnet, the controller sets the gNMI data on the nodes in the sibling's topology.

        Args:
            None

        Returns:
            None

        Raises:
            None
        '''

        while True:
            self.logger.debug("sleeping until next interval to run apps in controller " +
                            self.name() + "..." )
            time.sleep(self.config['interval'])

            # get queue for assigned siblings and run apps on changes
            for sibling in self.sibling_topo:
                self.logger.debug("Processing tasks and apps for sibling " + sibling)
                sibling_queue = self.queues[sibling]

                # get gNMI data from the real network
                # could be improved by using subscribe instead of get
                self.logger.debug("<-- Getting gNMI data from the sec sibling network...")

                # save old model for comparison until we implement subscriptions etc.
                old_nodes = copy.deepcopy(self.nodes)

                port = self.config['gnmi']['port']
                username = self.config['gnmi']['username']
                password = self.config['gnmi']['password']
                # if the gNMI data for the node's name exists in the model (e.g., not the case for a node that was added to the sibling's topology)
                if len(self.nodes) > 0 and self.siblings[sibling]['topology']['topology']['nodes'].get(node_name) is not None:
                    for node in self.nodes.items():
                        # if the sibling has a gnmi-sync config that defines nodes to sync
                        if self.config['siblings'][sibling].get('gnmi-sync') is not None and self.config['siblings'][sibling]['gnmi-sync'].get('nodes'):
                            # if the node matches the regex defined in the gnmi-sync config for the siblings
                            if re.fullmatch(self.config['siblings'][sibling]['gnmi-sync']['nodes'], node_name):
                                self.logger.debug("--> Getting gNMI data from node " + node_name + " in sibling " + sibling + "...")
                                host = self.config['clab_topology_prefix'] + "-" + self.config['clab_topology_name'] + "_" + sibling + "-" + node_name
                                with gNMIclient(target=(host, port), username=username, password=password, insecure=True) as gc:
                                    for path in self.config['gnmi']['paths']:
                                        result = gc.get(path=[path], datatype=self.config['gnmi']['datatype'])
                                        # for strip in config['gnmi']['strip']:
                                        #    # result = result.pop(strip)
                                        self.nodes[node[0]][path] = copy.deepcopy(result)

                                        # diff old and new model, excluding timestamp
                                        diff = DeepDiff(old_nodes, self.nodes, ignore_order=True, exclude_regex_paths="\\['timestamp'\\]")

                                        # if changes were detected, send an update to the controller queues
                                        if diff.tree != {}:
                                            for queue in self.queues:
                                                self.queues[queue].put({"type": "gNMI notification", 
                                                                            "source": sibling, 
                                                                            "node": node, 
                                                                            "path": path, 
                                                                            "data": result,
                                                                            "diff": diff.tree})

                # get task from queue for assigned sibling
                self.logger.debug("Checking queue for assigned sibling " + sibling)
                # if the queue is empty or sibling does not have a queue, continue
                task = None
                if self.queues.get(sibling) is not None and not self.queues[sibling].empty():
                    task = sibling_queue.get()
                    self.logger.debug("Controller " + self.name() + " got task for sibling " + 
                                    sibling + ": " + str(task) + " approx queue size: " +
                                    str(sibling_queue.qsize()))

                for app in self.apps.items():
                    # parallelized execution is suboptimal for now
                    self.logger.debug("=== Running App " + app[0] + " on Controller " + self.name() + " in pid " + str(self.process.pid) + " " + str(self.process.is_alive()) + "...")
                    asyncio.run(app[1].run(self.config, self.clab_topology_definition, sibling, self.nodes, self.real_nodes, self.queues, task))
                    # self.apps[app].run(self.config, self.clab_topology_definition, self.model, sibling, task)

                # setting gNMI data on nodes for running siblings if queue contained a task for the sibling (e.g., gNMI data in real network changed)
                if task is not None:
                    # check if task type and source are relevant for this controller
                    if task['type'] == "gNMI notification" and task['source'] == "realnet":
                        # if the task contains a diff (e.g., the gNMI data changed)
                        if task['diff'] is not {}:
                            notification_data = task['data']
                            node = task['node']
                            node_name = node[0]
                            path = task['path']
                            port = self.config['gnmi']['port']
                            username = self.config['gnmi']['username']
                            password = self.config['gnmi']['password']
                            # if the gNMI data for the node's name exists in the model (e.g., not the case for a node that was added to the sibling's topology)
                            if len(self.siblings[sibling]['topology']) > 0 and self.siblings[sibling]['topology']['nodes'].get(node_name) is not None:
                                # if the sibling has a gnmi-sync config that defines nodes to sync
                                if self.config['siblings'][sibling].get('gnmi-sync') is not None and self.config['siblings'][sibling]['gnmi-sync'].get('nodes'):
                                    # if the node matches the regex defined in the gnmi-sync config for the siblings
                                    if re.fullmatch(self.config['siblings'][sibling]['gnmi-sync']['nodes'], node_name):
                                        self.logger.debug("--> Setting gNMI data on node " + node_name + " in sibling " + sibling + ": " + str(notification_data) + "...")
                                        host = self.config['clab_topology_prefix'] + "-" + self.config['clab_topology_name'] + "_" + sibling + "-" + node_name
                                        try:
                                            with gNMIclient(target=(host, port), username=username, password=password, insecure=True) as gc:
                                                # for each notification in the notification data
                                                for notification in notification_data['notification']:
                                                    # if the notification is an update
                                                    if notification.get('update'):
                                                        for update in notification['update']:
                                                            # turn update to replace, gygnmi get delivers updates, but updating, e.g., ip address in interface config 
                                                            # requires replacing it, otherwise we get gRPC errors
                                                            result = gc.set(replace=[(str(path), dict(update['val']))])
                                                            self.logger.debug("gNMI set result: " + str(result))
                                                    else:
                                                        self.logger.info("UNSUPPORTED gNMI notification type: " + str(notification))
                                        except Exception as e:
                                            self.logger.error("Error getting gNMI data from " + host + " in sibling " + sibling + ": " + str(e))