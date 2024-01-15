from abc import ABC, abstractmethod


class Interface(ABC):
    def __init__(self):
        '''
        Constructor
        '''

    @abstractmethod
    def get(self, config, real_topo, sibling_topo, queues):
        pass

    @abstractmethod
    def set(self, config, real_topo, sibling_topo, queues):
        pass
