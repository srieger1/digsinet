from builders.builder import Builder

import yaml
import os

from kafka.client import KafkaClient


class containerlab(Builder):
    def __init__(self, config):
        '''
        Constructor
        '''
        super().__init__(config)

    def build_topology(self, config: dict, real_topo: dict, sibling: str, sibling_topo: dict, sibling_nodes: dict,
                       kafka_client: KafkaClient):
        # As we are using Containerlab, and the real network topology definition currently also uses Containerlab topology
        # definition as a standard, we can simply write the sibling topology to a new file and eventually start it using
        # Containerlab

        self.logger.info(f"Creating sibling {sibling} using containerlab builder...")
        # Write the sibling topology to a new file
        with open(f"./{config['name']}_sib_{sibling}.clab.yml", 'w',
                  encoding="utf-8") as stream:
            yaml.dump(sibling_topo, stream)

        sibling_config = config['siblings'].get(sibling)
        # If the sibling config exists and autostart is enabled
        running = False
        if sibling_config:
            if sibling_config.get('autostart'):
                running = self.start_topology(config, real_topo, sibling, sibling_topo, kafka_client)
        return running

    def start_topology(self, config: dict, real_topo: dict, sibling: str, sibling_topo: dict, kafka_client: KafkaClient):
        # Start the sibling topology using Containerlab
        self.logger.info(f"Starting sibling {sibling} using containerlab builder...")
        os.system(f"clab deploy {config['reconfigureContainers']} -t ./{config['name']}_sib_{sibling}.clab.yml")
        running = True
        return running
