from builders.builder import Builder
from config import Settings

import yaml
import os


class containerlab(Builder):
    def __init__(self, config, logger, reconfigure_containers):
        '''
        Constructor
        '''
        super().__init__(config, logger, reconfigure_containers)

    def build_topology(self, real_topo: dict, sibling: str, sibling_topo: dict, sibling_nodes: dict,
                       queues: dict):
        # As we are using Containerlab, and the real network topology definition currently also uses Containerlab topology
        # definition as a standard, we can simply write the sibling topology to a new file and eventually start it using
        # Containerlab

        self.logger.info(f"Creating sibling {sibling} using containerlab builder...")
        # Write the sibling topology to a new file
        with open(f"./{self.config.topology_name}_sib_{sibling}.clab.yml", 'w',
                  encoding="utf-8") as stream:
            yaml.dump(sibling_topo, stream)

        sibling_config = self.config.siblings.get(sibling)
        # If the sibling config exists and autostart is enabled
        running = False
        if sibling_config:
            if sibling_config.autostart:
                running = self.start_topology(real_topo, sibling, sibling_topo, queues)
        return running

    def start_topology(self, real_topo: dict, sibling: str, sibling_topo: dict, queues: dict):
        # Start the sibling topology using Containerlab
        self.logger.info(f"Starting sibling {sibling} using containerlab builder...")
        os.system(f"clab deploy {self.reconfigure_containers} -t ./{self.config.topology_name}_sib_{sibling}.clab.yml")
        running = True
        return running
