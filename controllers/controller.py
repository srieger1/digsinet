'''Controller base class'''
from abc import ABC, abstractmethod

from multiprocessing import Process

import asyncio

import importlib
import copy
import re
import time

from interfaces.gnmi import gnmi

class Controller(ABC):
    '''
    Abstract base class for controllers.

    Attributes:
        config (dict): contents of configuration file and derived supplemental configuration values.
        real_topology_definition (dict): real network topology definition (e.g., containerlab YAML)
        real_nodes (dict): nodes in the real network
        queues (dict): queues for, e.g., for all siblings
        
    Methods:
        name()
        import_app(app: str, module: str)
        build_topology(sibling: str, config: dict, topology_definition: dict)
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


    def __init__(self, config: dict, real_topology_definition: dict, real_nodes: dict, sibling: str, queues: dict):
            '''
            Initialize the controller.

            Args:
                config (dict): contents of configuration file and derived supplemental configuration
                    values.
                real_topology_definition (dict): real network topology definition (e.g., containerlab YAML)
                real_nodes (dict): nodes in the real network
                sibling (str): name of the sibling to create
                queues (dict): queues for, e.g., for all siblings

            Returns:
                None

            Raises:
                None
            '''

            self.config = config # contents of configuration file and derived supplemental
                # configuration values.
            self.real_topo = {} # topology definition of the real network
            self.real_topo['topology'] = real_topology_definition # topology definition of
                # the real network
            self.real_topo['nodes'] = real_nodes # nodes in the real network
            self.queues = queues # queues for, e.g., for all siblings

            self.logger = config['logger']

            # import builder
            self.logger.debug("Loading builder for controller " + self.name() + "...")
            configured_sibling_builder = config['controllers'][self.name()]['builder']
            builder_module = importlib.import_module(config['builders'][configured_sibling_builder]['module'])
            builder_class = getattr(builder_module, configured_sibling_builder)
            builder_instance = builder_class(config)
            self.builder = builder_instance

            # import apps
            self.apps = {} # apps to run on the siblings
            for app in config['apps']:
                # if app is used by controller in config
                if config['controllers'][self.name()].get('apps'):
                    if app in config['controllers'][self.name()]['apps']:
                        self.__import_app(app, config['apps'][app]['module'])

            self.siblings = [] # siblings of the controller
            self.siblings.append(sibling)
            self.sibling_topo = {} # topology state of the siblings

            # start the controller process
            self.process = Process(target=self.__run, name="Controller " + self.name())
            # self.process.daemon = True
            self.process.start()
            self.logger.info("Controller: " + self.name() + " has Process id: " + str(self.process.pid))
            # self.process.join()


    def __import_app(self, app: str, module: str):
        '''
        Import an application into this controller.

        Args:
            app (str): name of the app in the dictionary of the controller
            module (str): module name of the app to import

        Returns:
            None

        Raises:
            None
        '''

        # import the module
        self.logger.debug("Loading app " + app + " for controller " + self.name() + "...")
        app_module = importlib.import_module(module)
        # create an instance of the app
        app_class = getattr(app_module, app)
        app_instance = app_class(self.config, self.real_topo)
        self.apps[app] = app_instance


    def __import_interface(self, interface: str, module: str, sibling: str):
        '''
        Import an interface into this controller.

        Args:
            interface (str): name of the interface in the dictionary of the controller
            module (str): module name of the app to import

        Returns:
            None

        Raises:
            None
        '''

        # import the module
        self.logger.debug("Loading interface " + interface + " for controller " + self.name() + "...")
        interface_module = importlib.import_module(module)
        # create an instance of the app
        interface_class = getattr(interface_module, interface)
        interface_instance = interface_class(self.config, sibling)
        return interface_instance


    def __build_topology(self, sibling: str, config: dict, real_topology_definition: dict):
        '''
        Build the sibling for this controller.

        Implements creation of a topology for the sibling and optionally starting it.
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

        # create nodes for the sibling network model
        sibling_nodes = {}
        for node in sibling_topology_definition['topology']['nodes'].items():
            sibling_nodes[node[0]] = {}

        # Create the sibling topology
        self.logger.debug("Creating sibling " + sibling + "using builder " + self.builder.__module__ + "...")
        running = False
        running = self.builder.build_topology(config, real_topology_definition, sibling, sibling_topology_definition, sibling_nodes, self.queues)
    
        # Import the sibling's interfaces
        interfaces = {}
        for interface in config['siblings'][sibling]['interfaces']:
            # if interface is used by controller in config
            if config['controllers'][self.name()].get('interfaces'):
                if interface in config['controllers'][self.name()]['interfaces']:
                    interfaces[interface] = self.__import_interface(interface, config['interfaces'][interface]['module'], sibling)

        # Return the sibling's topology state
        sibling_topo_state = {'name': sibling, 'topology': sibling_topology_definition, 'nodes': sibling_nodes, 'interfaces': interfaces, 'running': running}
        return sibling_topo_state


    def __run(self):
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
            for sibling in self.siblings:
                # if sibling was already built, get its topology and data updates using associated interfaces
                if self.sibling_topo.get(sibling) is not None:
                    if self.sibling_topo[sibling]['running'] is False:
                        # if the sibling is not running, don't run interface updates and apps
                        continue
                    sib_nodes = self.sibling_topo[sibling]['nodes']

                    # get general interface config union with siblings interface config? e.g., datatype set in general config, but overridden in sibling config etc.

                    # get interface data from sibling network
                    for interface in self.sibling_topo[sibling]['interfaces']:
                        interface_instance = self.sibling_topo[sibling]['interfaces'][interface]
                        self.logger.debug("Getting interface data for " + interface + " from sibling " + sibling + "...")
                        self.sibling_topo[sibling]['nodes'] = interface_instance.getNodeUpdateDiff(sib_nodes,  self.queues)

                self.logger.debug("Processing tasks and apps for sibling " + sibling)
                sib_queue = self.queues[sibling]
                # get task from queue for assigned sibling
                self.logger.debug("Checking queue for assigned sibling " + sibling)
                task = None
                # if the queue is empty or sibling does not have a queue, continue

                if self.queues.get(sibling) is not None and not self.queues[sibling].empty():
                    task = sib_queue.get()
                    self.logger.debug("Controller " + self.name() + " got task for sibling " + 
                                    sibling + ": " + str(task) + " approx queue size: " +
                                    str(sib_queue.qsize()))

                    # setting gNMI data on nodes for running siblings if queue contained a task for the sibling (e.g., gNMI data in real network changed)
                    if task is not None:
                        # check if task type and source are relevant for this controller
                        if task['type'] == "gNMI notification" and task['source'] == "realnet" and self.sibling_topo.get(sibling) is not None:
                            # if the task contains a diff (e.g., the gNMI data changed)
                            if task['diff'] is not {}:
                                notification_data = task['data']
                                node = task['node']
                                node_name = node
                                path = task['path']

                                gnmi_instance = gnmi(self.config, sibling)
                                gnmi_instance.setNodeUpdate(sib_nodes, node_name, path, notification_data)
                        if task['type'] == "topology build request" and task['sibling'] == sibling:
                            # build the sibling topology
                            self.sibling_topo[sibling] = self.__build_topology(sibling, self.config, self.real_topo['topology'])
                            for queue in self.queues:
                                self.queues[queue].put({"type": "topology build response",
                                                        "source": sibling,
                                                        "sibling": sibling,
                                                        "topology": self.sibling_topo[sibling]['topology'],
                                                        "nodes": self.sibling_topo[sibling]['nodes'],
                                                        "interfaces": self.sibling_topo[sibling]['interfaces'],
                                                        "running": self.sibling_topo[sibling]['running']})

                # run apps assigned to the controller
                if self.sibling_topo.get(sibling) is not None:
                    for app in self.apps.items():
                        # parallelized execution is suboptimal for now
                        self.logger.debug("=== Running App " + app[0] + " on Controller " + self.name() + " in pid " + str(self.process.pid) + " " + str(self.process.is_alive()) + "...")
                        asyncio.run(app[1].run(self.sibling_topo[sibling], self.queues, task))
                        # self.apps[app].run(self.config, self.siblings[sibling]['topology'], self.model, sibling, task)