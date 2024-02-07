'''Interface base class for DigSiNet'''
from abc import ABC, abstractmethod
from multiprocessing import Queue


class Interface(ABC):
    '''
    Abstract base class for interfaces.
    '''

    logger = None

    config = dict()
    interface_config = dict()
    topology_interface_config = dict()

    def __init__(self, config: dict, target_topology: str):
        '''
        Constructor
        '''
        self.logger = config['logger']

        self.config = config

        self.topology_interface_config = self.getTopologyInterfaceConfig(target_topology)

    def getTopologyInterfaceConfig(self, target: str):
        if target == "realnet":
            if self.config[target]["interfaces"] and self.config[target]["interfaces"]["gnmi"]:
                return self.config[target]['interfaces']["gnmi"]
        else:
            if self.config["siblings"][target]["interfaces"] and self.config["siblings"][target]["interfaces"]["gnmi"]:
                return self.config["siblings"][target]["interfaces"]["gnmi"]

    @abstractmethod
    def getNodesUpdate(self, nodes: dict, queues: dict[Queue], diff: bool = False):
        pass

    @abstractmethod
    def setNodeUpdate(self, nodes: dict, node_name: str, path: str, notification_data: dict):
        pass

    @abstractmethod
    def set(self, nodes: dict, node_name: str, op: str, data: dict):
        pass
