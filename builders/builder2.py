from abc import ABC, abstractmethod
from topology import Topology


class TopologyBuilder(ABC):
    def __init__(self, topology: Topology):
        self.topology = topology

    @abstractmethod
    def build_topology(self):
        pass

    @abstractmethod
    def destroy_topology(self):
        pass
