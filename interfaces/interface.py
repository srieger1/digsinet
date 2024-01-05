from abc import ABC, abstractmethod


class Interface(ABC):
    def __init__(self):
        '''
        Constructor
        '''

    @abstractmethod
    async def get(self, config, clab_topology_definition, sibling, sibling_clab_topo, real_nodes,
            queues, task):
        pass

    @abstractmethod
    async def set(self, config, clab_topology_definition, sibling, sibling_clab_topo, real_nodes,
            queues, task):
        pass
