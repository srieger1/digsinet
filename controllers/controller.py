'''Controller base class for DigSiNet.'''
from abc import ABC, abstractmethod

from multiprocessing import Process
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
        clab_topology_definition (dict): contents of containerlab (YAML-based) topology file
        sibling (str): name of the sibling associated with this controller (as defined in the config
          file)
        real_nodes (dict): nodes in the real network
        queues (dict): queues for, e.g., for all siblings
        
    Methods:
        name()
        add_sibling(sibling: str)
        import_app(app: str, module: str)
        build_sibling(config: dict, clab_topology_definition: dict)
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
    def name(self, name):
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


    apps = {} # apps to run on the sibling
    sibling_clab_topo = {} # topology for the sibling
    nodes = {} # nodes in the sibling's topology

    def __init__(self, config, clab_topology_definition, sibling, real_nodes, queues):
        '''
        Initialize the controller.

        Args:
            config (dict): contents of configuration file and derived supplemental configuration
                values.
            clab_topology_definition (dict): contents of containerlab (YAML-based) topology file
            sibling (str): name of the sibling associated with this controller (as defined in the
                config file)
            real_nodes (dict): nodes in the real network
            queues (dict): queues for, e.g., for all siblings

        Returns:
            None

        Raises:
            None
        '''

        self.config = config # contents of configuration file and derived supplemental
            # configuration values.
        self.clab_topology_definition = clab_topology_definition # contents of containerlab
            # (YAML-based) topology file
        self.sibling = sibling # name of the siblings associated with this controller
        self.real_nodes = real_nodes # nodes in the real network
        self.queues = queues # queues for, e.g., for all siblings

        self.logger = config['logger']

        # import apps
        for app in config['apps']:
            # if app is used by controller in config
            if config['controllers'][config['siblings'][sibling]['controller']].get('apps'):
                if app in config['controllers'][config['siblings'][sibling]['controller']]['apps']:
                    self.import_app(app, config['apps'][app]['module'])

        # start the controller process
        self.process = Process(target=self.run)
        # self.process.daemon = True
        self.process.start()
        self.logger.debug("Process id: " + str(self.process.pid))
        # self.process.join()


    # def add_sibling(self, sibling):
    #     '''
    #     Add a sibling to this controller.

    #     Args:
    #         sibling (str): name of the sibling to add
        
    #     Returns:
    #         None

    #     Raises:
    #         None
    #     '''

    #     if self.sibling is None:
    #         self.sibling = list()
    #     self.sibling.append(sibling)


    def import_app(self, app, module):
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


    def build_sibling(self, config, clab_topology_definition):
        '''
        Build the sibling for this controller.

        Implements creation of a containerlab topology for the sibling and optionally starting it.
        Can be overridden by subclasses to implement additional functionality (e.g., supporting
            alternatives to containerlab).

        Args:
            config (dict): contents of configuration file and derived supplemental configuration
                values.
            clab_topology_definition (dict): contents of containerlab (YAML-based) topology file

        Returns:
            dict: sibling's topology
            bool: whether the sibling is running    

        Raises:
            None
        '''

        # Get the topology for the sibling
        sibling_clab_topo = copy.deepcopy(clab_topology_definition)
        # Update the name in the topology to reflect the sibling
        sibling_clab_topo['name'] = clab_topology_definition['name'] + "_" + self.sibling
        # Topology adjustments for the sibling
        if config['siblings'][self.sibling] is not None and config['siblings'][self.sibling] \
            .get('topology-adjustments'):
            for adjustment in config['siblings'][self.sibling]['topology-adjustments']:
                match adjustment:
                    case 'node-remove':
                        for node in sibling_clab_topo['topology']['nodes'].copy().items():
                            if re.fullmatch(config['siblings'][self.sibling] \
                                    ['topology-adjustments']['node-remove'], node[0]):
                                sibling_clab_topo['topology']['nodes'].pop(node[0])

                                # Remove links to removed nodes from the topology
                            for link in sibling_clab_topo['topology']['links']:
                                if any(endpoint.startswith(node[0] + ":") for endpoint in link['endpoints']):
                                    sibling_clab_topo['topology']['links'].pop(sibling_clab_topo['topology']['links'].index(link))
                    case 'node-add':
                        for node in config['siblings'][self.sibling]['topology-adjustments']['node-add']:
                            node_config = config['siblings'][self.sibling]['topology-adjustments']['node-add'][node]
                            sibling_clab_topo['topology']['nodes'][node] = node_config
                    case 'link-remove':
                        # Remove links from the topology
                        for link in config['siblings'][self.sibling]['topology-adjustments'] \
                                ['link-remove']:
                            sibling_clab_topo['topology']['links'].pop(
                                sibling_clab_topo['topology']['links'].index(link))
                    case 'link-add':
                        # Add links to the topology
                        for link in config['siblings'][self.sibling]['topology-adjustments'] \
                                ['link-add']:
                            sibling_clab_topo['topology']['links'].append(link)

        # Write the sibling topology to a new file
        with open("./" + config['name'] + "_sib_" + self.sibling + ".clab.yml", 'w',
                encoding="utf-8") as stream:
            yaml.dump(sibling_clab_topo, stream)
        # Set the sibling topology in the controller's model
        self.sibling_clab_topo[self.sibling] = copy.deepcopy(sibling_clab_topo)

        # create nodes for the sibling network model
        for node in sibling_clab_topo['topology']['nodes'].items():
            self.nodes[node[0]] = dict()

        sibling_config = config['siblings'].get(self.sibling)
        # If the sibling config exists and autostart is enabled
        running = False
        if sibling_config:
            if sibling_config.get('autostart'):
                # Deploy the sibling topology using Containerlab
                self.logger.info("Deploying sibling " + self.sibling + "...")
                os.system(f"clab deploy {config['reconfigureContainers']} -t {config['name']}_sib_{self.sibling}.clab.yml")
                running = True

        return {'clab_topology': sibling_clab_topo, 'running': running}


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

        # get queue for assigned sibling and run apps on changes
        sibling_queue = self.queues[self.sibling]

        while True:
            self.logger.debug("sleeping until next interval to run apps in controller " +
                              self.name() + "..." )
            time.sleep(self.config['interval'])

            # get task from queue for assigned sibling
            self.logger.debug("Checking queue for assigned sibling " + self.sibling)
            # if the queue is empty or sibling does not have a queue, continue
            task = None
            if self.queues.get(self.sibling) is not None and not self.queues[self.sibling].empty():
                task = sibling_queue.get()
                self.logger.debug("Controller " + self.name() + " got task for sibling " + 
                                self.sibling + ": " + str(task) + " approx queue size: " +
                                str(sibling_queue.qsize()))

            for app in self.apps.items():
                # parallelized execution is suboptimal for now
                self.logger.debug("=== Running App " + app[0] + " on Controller " + self.name() + " in pid " + str(self.process.pid) + " " + str(self.process.is_alive()) + "...")
                asyncio.run(app[1].run(self.config, self.clab_topology_definition, self.sibling, self.nodes, self.real_nodes, self.queues, task))
                # self.apps[app].run(self.config, self.clab_topology_definition, self.model, self.sibling, task)

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
                        if len(self.nodes) > 0 and self.nodes.get(node_name) is not None:
                            # if the sibling has a gnmi-sync config that defines nodes to sync
                            if self.config['siblings'][self.sibling].get('gnmi-sync') is not None and self.config['siblings'][self.sibling]['gnmi-sync'].get('nodes'):
                                # if the node matches the regex defined in the gnmi-sync config for the siblings
                                if re.fullmatch(self.config['siblings'][self.sibling]['gnmi-sync']['nodes'], node_name):
                                    self.logger.debug("--> Setting gNMI data on node " + node_name + " in sibling " + self.sibling + ": " + str(notification_data) + "...")
                                    host = self.config['clab_topology_prefix'] + "-" + self.clab_topology_definition['name'] + "_" + self.sibling + "-" + node_name
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
                                    except:
                                        self.logger.error("Error connecting to " + host + " in sibling " + self.sibling)
