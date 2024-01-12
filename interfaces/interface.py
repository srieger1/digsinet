from abc import ABC, abstractmethod


class Interface(ABC):
    def __init__(self):
        '''
        Constructor
        '''

    @abstractmethod
    async def get(self, config, real_topo, sibling_topo, queues):
        pass

    @abstractmethod
    async def set(self, config, real_topo, sibling_topo, queues):
        pass
