from abc import ABC, abstractmethod
from config import Settings
from event.eventbroker import EventBroker

class Builder(ABC):
    logger = None

    def __init__(self, config: Settings, logger, reconfigure_containers):
        '''
        Constructor
        '''
        self.config = config
        self.logger = logger
        self.reconfigure_containers = reconfigure_containers

    @abstractmethod
    def build_topology(self, real_topo: dict, sibling: str, sibling_topo: dict, sibling_nodes: dict,
                       broker: EventBroker):
        pass

    @abstractmethod
    def start_topology(self, real_topo: dict, sibling: str, sibling_topo: dict, broker: EventBroker):
        pass
