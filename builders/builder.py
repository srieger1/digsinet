from abc import ABC, abstractmethod


class Builder(ABC):
    def __init__(self):
        '''
        Constructor
        '''

    @abstractmethod
    async def build_sibling(self, config, real_topo, sibling_topo, queues):
        pass
