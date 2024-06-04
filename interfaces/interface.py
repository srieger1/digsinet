"""Interface base class for DigSiNet"""
from abc import ABC, abstractmethod
from multiprocessing import Queue
from config import Settings, InterfaceSettings


class Interface(ABC):
    """
    Abstract base class for interfaces.
    """

    logger = None

    config: Settings
    interface_config = dict()
    topology_interface_config: InterfaceSettings

    def __init__(self, config: Settings, target_topology: str, logger, topology_prefix: str, topology_name: str):
        '''
        Constructor
        '''
        self.logger = logger

        self.config = config

        self.topology_interface_config = self.getTopologyInterfaceConfig(target_topology)
        self.topology_prefix = topology_prefix
        self.topology_name = topology_name

    def getTopologyInterfaceConfig(self, target: str) -> InterfaceSettings:
        if target == "realnet":
            if self.config.realnet.interfaces.get('gnmi') is not None:
                return self.config.realnet.interfaces.get('gnmi')
        else:
            if self.config.siblings.get(target).interfaces.get('gnmi') is not None:
                return self.config.siblings.get(target).interfaces.get('gnmi')

    @abstractmethod
    def getNodesUpdate(self, nodes: dict, queues: dict[Queue], diff: bool = False):
        pass

    @abstractmethod
    def setNodeUpdate(self, nodes: dict, node_name: str, path: str, notification_data: dict):
        pass

    @abstractmethod
    def set(self, nodes: dict, node_name: str, op: str, data: dict):
        pass
