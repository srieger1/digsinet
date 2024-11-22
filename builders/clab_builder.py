from builders.builder2 import TopologyBuilder
from topology import Topology
import yaml


class TopologyDumper:
    def __init__(self, topology: Topology):
        self.topology = topology

    def __to_dict(self):
        return {
            'name': self.topology.name,
            'topology': {
                'nodes': {
                    node.name: {
                        'kind': node.kind,
                        'image': f"{node.kind}:latest",
                    }
                    for node in self.topology.nodes
                },
                'links': [
                    {
                        'endpoints': [
                            f"{link.name_from}:{link.interface_from}",
                            f"{link.name_to}:{link.interface_to}",
                        ]
                    }
                    for link in self.topology.links
                ]
            }
        }

    def dump(self) -> str:
        data = self.__to_dict()
        return yaml.safe_dump(data, default_flow_style=False, sort_keys=False)


class ClabBuilder(TopologyBuilder):
    def __init__(self, topology: Topology):
        super().__init__(topology)

    def build_topology(self):
        pass

    def destroy_topology(self):
        pass
