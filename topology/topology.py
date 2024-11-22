from .link import Link
from .node import Node
from typing import List

__all__ = ["Topology", "TopologyBuilder"]


class Topology:
    def __init__(self):
        self.nodes: List[Node] = []
        self.links: List[Link] = []

    @staticmethod
    def builder():
        return TopologyBuilder()



class TopologyBuilder:
    def __init__(self) -> None:
        self._topo = Topology()

    def add_node(self, name: str, kind: str) -> None:
        self._topo.nodes.append(Node(name, kind, []))

    def add_link(
        self,
        node_from: str,
        node_to: str,
        interface_from: str,
        interface_to: str,
    ) -> None:
        # assert
        assert any(node.name == node_from for node in self._topo.nodes)
        assert any(node.name == node_to for node in self._topo.nodes)
        self._topo.links.append(
            Link(node_from, node_to, interface_from, interface_to)
        )

    def clear(self) -> None:
        self._topo.nodes = []
        self._topo.links = []

    def build(self) -> Topology:
        return self._topo
