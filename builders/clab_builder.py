from builders.builder2 import TopologyBuilder
from topology import Topology
import yaml
import subprocess


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
        topology_spec = TopologyDumper(self.topology).dump()
        try:
            proc = subprocess.Popen(
                f"clab deploy --topo -",
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = proc.communicate(topology_spec)
            if proc.returncode != 0:
                raise RuntimeError(f"Topology deployment failed with code {proc.returncode}: {stderr}")
        except FileNotFoundError:
            raise RuntimeError(f"Containerlab is required to use the clab builder.")

    def destroy_topology(self):
        pass
