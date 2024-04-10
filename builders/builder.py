from abc import ABC, abstractmethod
from queues.client import MessageQueueClient


class Builder(ABC):
    logger = None

    def __init__(self, config: dict):
        '''
        Constructor
        '''
        self.logger = config['logger']

    @abstractmethod
    def build_topology(self, config: dict, real_topo: dict, sibling: str, sibling_topo: dict, sibling_nodes: dict,
                       mq_client: MessageQueueClient):
        pass

    @abstractmethod
    def start_topology(self, config: dict, real_topo: dict, sibling: str, sibling_topo: dict, sibling_nodes: dict,
                       mq_client: MessageQueueClient):
        pass
