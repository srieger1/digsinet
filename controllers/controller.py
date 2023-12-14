from multiprocessing import Process
import asyncio

import importlib

from pygnmi.client import gNMIclient

import re
import time

class Controller():
    apps = dict()

    def __init__(self, config, clab_topology_definition, model, sibling):
        self.config = config
        self.clab_topology_definition = clab_topology_definition
        self.model = model
        self.sibling = sibling
        self.apps = dict()

        self.logger = config['logger']

        # import apps
        for app in config['apps']:
            # if app is used by controller in config
            if config['controllers'][config['siblings'][sibling]['controller']].get('apps'):
                if app in config['controllers'][config['siblings'][sibling]['controller']]['apps']:
                    self.import_app(app, config['apps'][app]['module'])

        # start the controller process
        self.process = Process(target=self.run)
        self.name = "base"
        # self.process.daemon = True
        self.process.start()
        self.logger.debug("Process id: " + str(self.process.pid))
        # self.process.join()

    def import_app(self, app, module):
        # import the module
        self.logger.debug("Loading app " + app + " for controller " + __name__ + "...")
        self.apps[app] = importlib.import_module(module)

    def run(self):
        # get queue for assigned sibling and run apps on changes
        while True:
            self.logger.debug("sleeping until next interval to run apps in controller " + self.name + "..." )
            time.sleep(self.config['interval'])

            # get task from queue for assigned sibling
            self.logger.debug("Checking queue for assigned sibling " + self.sibling)
            # if the queue is empty or sibling does not have a queue, continue
            task = None
            if self.model['queues'].get(self.sibling) is not None and not self.model['queues'][self.sibling].empty():
                task = self.model['queues'][self.sibling].get()
                self.logger.debug("Controller " + self.name + " got task for sibling " + self.sibling + ": " + str(task))

            for app in self.apps:
                # parallelized execution is suboptimal for now
                self.logger.debug("=== Running App " + app + " on Controller " + self.name + " in pid " + str(self.process.pid) + " " + str(self.process.is_alive()) + "...")
                asyncio.run(self.apps[app].run(self.config, self.clab_topology_definition, self.model, self.sibling, task))
                # self.apps[app].run(self.config, self.clab_topology_definition, self.model, self.sibling, task)

            # setting gNMI data on nodes for running siblings if queue contained a task for the sibling (e.g., gNMI data in real network changed)
            if task is not None:
                port = self.config['gnmi']['port']
                username = self.config['gnmi']['username']
                password = self.config['gnmi']['password']
                for sibling in self.model['siblings']:
                    # if the sibling is running
                    if self.model['siblings'][sibling].get('running'):
                        for node in self.model['siblings'][sibling]['clab_topology']['topology']['nodes'].items():
                            # if the sibling has a gnmi-sync config and the node matches the regex
                            if self.config['siblings'][sibling].get('gnmi-sync') is not None and self.config['siblings'][sibling]['gnmi-sync'].get('nodes'):
                                if re.fullmatch(self.config['siblings'][sibling]['gnmi-sync']['nodes'], node[0]):
                                    # if the gNMI data for the node's name exists in the model (e.g., not the case for a node that was added to the sibling's topology)
                                    if self.model['nodes'].get(node[0]) is not None:
                                        self.logger.debug("--> Setting gNMI data on node " + node[0] + " in sibling " + sibling + "...")
                                        host = self.config['clab_topology_prefix'] + "-" + self.clab_topology_definition['name'] + "_" + sibling + "-" + node[0]
                                        with gNMIclient(target=(host, port), username=username, password=password, insecure=True) as gc:
                                            # for each path in the model for the node
                                            for path in self.model['nodes'][node[0]]:
                                                for notification in self.model['nodes'][node[0]][path]['notification']:
                                                    # if the notification is an update
                                                    if notification.get('update'):
                                                        for update in notification['update']:
                                                            result = gc.set(update=[(str(path), dict(update['val']))])
