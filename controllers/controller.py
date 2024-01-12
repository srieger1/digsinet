'''Controller base class for DigSiNet.'''
from abc import ABC, abstractmethod

from multiprocessing import Process, Semaphore
import asyncio

import importlib
import copy
import os
import re
import time

import yaml
from pygnmi.client import gNMIclient


class Controller(ABC):
    '''
    Abstract base class for sibling controllers.

    Attributes:
        config (dict): contents of configuration file and derived supplemental configuration values.
        real_topology_definition (dict): real network topology definition (e.g., containerlab YAML)
        real_nodes (dict): nodes in the real network
        queues (dict): queues for, e.g., for all siblings
        
    Methods:
        name()
        import_app(app: str, module: str)
        build_sibling(sibling: str, config: dict, topology_definition: dict)
        run()
    '''


    @property
    def name(self):
        '''
        Name of the controller.

        Args:
            None

        Returns:
            str: name of the controller

        Raises:
            None
        '''

        return self._name
    
    @name.setter
    @abstractmethod
    def name(self, name: str):
        '''
        Name of the controller.

        Args:
            None

        Returns:
            str: name of the controller

        Raises:
            None
        '''

        self._name = name


    apps = {} # apps to run on the siblings
    real_topo = {} # topology definition of the real network 
    sibling_topo = {} # topology definition and name of siblings associated with this controller

    def __init__(self, config: dict, real_topology_definition: dict, real_nodes: dict, queues: dict):
        '''
        Initialize the controller.

        Args:
            config (dict): contents of configuration file and derived supplemental configuration
                values.
            topology_definition (dict): real network topology definition (e.g., containerlab YAML)
            real_nodes (dict): nodes in the real network
            queues (dict): queues for, e.g., for all siblings

        Returns:
            None

        Raises:
            None
        '''

        self.config = config # contents of configuration file and derived supplemental
            # configuration values.
        self.real_topo['topology'] = real_topology_definition # topology definition of
            # the real network
        self.real_topo['nodes'] = real_nodes # nodes in the real network
        self.queues = queues # queues for, e.g., for all siblings

        self.logger = config['logger']

        # import apps
        for app in config['apps']:
            # if app is used by controller in config
            if config['controllers'][self.name()].get('apps'):
                if app in config['controllers'][self.name()]['apps']:
                    self.import_app(app, config['apps'][app]['module'])

        # start the controller process
        self.process = Process(target=self.run)
        # self.process.daemon = True
        self.process.start()
        self.logger.debug("Process id: " + str(self.process.pid))
        # self.process.join()


    def import_app(self, app: str, module: str):
        '''
        Import a DigSiNet application into this controller.

        Args:
            app (str): name of the app in the dictionary of the controller
            module (str): module name of the app to import

        Returns:
            None

        Raises:
            None
        '''

        # import the module
        self.logger.debug("Loading app " + app + " for controller " + __name__ + "...")
        app_module = importlib.import_module(module)
        # create an instance of the app
        app_class = getattr(app_module, app)
        app_instance = app_class()
        self.apps[app] = app_instance


    def build_sibling(self, sibling: str, config: dict, real_topology_definition: dict):
        '''
        Build the sibling for this controller.

        Implements creation of a containerlab topology for the sibling and optionally starting it.
        Can be overridden by subclasses to implement additional functionality (e.g., supporting
            alternatives to containerlab).

        Args:
            sibling (str): name of the sibling to create
            config (dict): contents of configuration file and derived supplemental configuration
                values.
            real_topology_definition (dict): real network topology definition (e.g., containerlab YAML)

        Returns:
            dict: sibling's topology definition
            bool: whether the sibling is running    

        Raises:
            None
        '''

        self.sibling_topo[sibling] = {} # add sibling to controller

        # Get the topology for the sibling
        sibling_topology_definition = copy.deepcopy(real_topology_definition)
        # Update the name in the topology to reflect the sibling
        sibling_topology_definition['name'] = real_topology_definition['name'] + "_" + sibling
        # Topology adjustments for the sibling
        if config['siblings'][sibling] is not None and config['siblings'][sibling] \
            .get('topology-adjustments'):
            for adjustment in config['siblings'][sibling]['topology-adjustments']:
                match adjustment:
                    case 'node-remove':
                        for node in sibling_topology_definition['topology']['nodes'].copy().items():
                            if re.fullmatch(config['siblings'][sibling] \
                                    ['topology-adjustments']['node-remove'], node[0]):
                                sibling_topology_definition['topology']['nodes'].pop(node[0])

                            # Remove links to removed nodes from the topology
                            for link in sibling_topology_definition['topology']['links']:
                                if any(endpoint.startswith(node[0] + ":") for endpoint in link['endpoints']):
                                    sibling_topology_definition['topology']['links'].pop(sibling_topology_definition['topology']['links'].index(link))
                    case 'node-add':
                        for node in config['siblings'][sibling]['topology-adjustments']['node-add']:
                            node_config = config['siblings'][sibling]['topology-adjustments']['node-add'][node]
                            sibling_topology_definition['topology']['nodes'][node] = node_config
                    case 'link-remove':
                        # Remove links from the topology
                        for link in config['siblings'][sibling]['topology-adjustments'] \
                                ['link-remove']:
                            sibling_topology_definition['topology']['links'].pop(
                                sibling_topology_definition['topology']['links'].index(link))
                    case 'link-add':
                        # Add links to the topology
                        for link in config['siblings'][sibling]['topology-adjustments'] \
                                ['link-add']:
                            sibling_topology_definition['topology']['links'].append(link)

        # Write the sibling topology to a new file
        with open("./" + config['name'] + "_sib_" + sibling + ".clab.yml", 'w',
                encoding="utf-8") as stream:
            yaml.dump(sibling_topology_definition, stream)

        # create nodes for the sibling network model
        sibling_nodes = {}
        for node in sibling_topology_definition['topology']['nodes'].items():
            sibling_nodes[node[0]] = {}
            sibling_nodes[node[0]]['gNMIWriteSemaphore'] = Semaphore(1)

        sibling_config = config['siblings'].get(sibling)
        # If the sibling config exists and autostart is enabled
        running = False
        if sibling_config:
            if sibling_config.get('autostart'):
                # Deploy the sibling topology using Containerlab
                self.logger.info("Deploying sibling " + sibling + "...")
                os.system(f"clab deploy {config['reconfigureContainers']} -t {config['name']}_sib_{sibling}.clab.yml")
                running = True

        # Set the sibling's topology state in the controller's model
        sibling_topo_state = {'name': sibling, 'topology': sibling_topology_definition, 'nodes': sibling_nodes, 'running': running}
        self.sibling_topo[sibling].update(sibling_topo_state)
        return {'topology': sibling_topology_definition, 'running': running}


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
                sib_nodes = self.sibling_topo[sibling]['nodes']
                sib_config = self.config['siblings'][sibling]

                self.logger.debug("Processing tasks and apps for sibling " + sibling)
                sib_queue = self.queues[sibling]
                # get task from queue for assigned sibling
                self.logger.debug("Checking queue for assigned sibling " + sibling)
                # if the queue is empty or sibling does not have a queue, continue
                task = None
                if self.queues.get(sibling) is not None and not self.queues[sibling].empty():
                    task = sib_queue.get()
                    self.logger.debug("Controller " + self.name() + " got task for sibling " + 
                                    sibling + ": " + str(task) + " approx queue size: " +
                                    str(sib_queue.qsize()))

                for app in self.apps.items():
                    # parallelized execution is suboptimal for now
                    self.logger.debug("=== Running App " + app[0] + " on Controller " + self.name() + " in pid " + str(self.process.pid) + " " + str(self.process.is_alive()) + "...")
                    asyncio.run(app[1].run(self.config, self.real_topo, self.sibling_topo[sibling], self.queues, task))
                    # self.apps[app].run(self.config, self.siblings[sibling]['topology'], self.model, sibling, task)

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
                            if len(sib_nodes) > 0 and sib_nodes.get(node_name) is not None:
                                # if the sibling has a gnmi-sync config that defines nodes to sync
                                if sib_config.get('gnmi-sync') is not None and sib_config['gnmi-sync'].get('nodes'):
                                    # if the node matches the regex defined in the gnmi-sync config for the siblings
                                    if re.fullmatch(sib_config['gnmi-sync']['nodes'], node_name):
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
                                                            sib_nodes[node_name]['gNMIWriteSemaphore'].acquire()
                                                            result = gc.set(replace=[(str(path), dict(update['val']))])
                                                            sib_nodes[node_name]['gNMIWriteSemaphore'].release()
                                                            self.logger.debug("gNMI set result: " + str(result))
                                                    else:
                                                        self.logger.info("UNSUPPORTED gNMI notification type: " + str(notification))
                                        except Exception as e:
                                            self.logger.error("Error getting gNMI data from " + host + " in sibling " + sibling + ": " + str(e))
