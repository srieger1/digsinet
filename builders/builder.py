from abc import ABC, abstractmethod


class Builder(ABC):
    logger = None


    def __init__(self, config: dict):
        '''
        Constructor
        '''
        self.logger = config['logger']


    @abstractmethod
    def build_topology(self, config: dict, real_topo: dict, sibling: str, sibling_topo: dict, sibling_nodes: dict, queues: dict):
        pass


    @abstractmethod
    def start_topology(self, config: dict, real_topo: dict, sibling: str, sibling_topo: dict, sibling_nodes: dict, queues: dict):
        pass
