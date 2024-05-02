from controllers.controller import Controller
from kafka.client import KafkaClient


class te(Controller):
    def __init__(self, config: dict, real_topology_definition: dict, real_nodes: dict, sibling: str, kafka_client: KafkaClient):
        super().__init__(config, real_topology_definition, real_nodes, sibling, kafka_client)

    def name(self):
        return "te"

    def __build_topology(self, sibling, config, real_topology_definition):
        return super().__build_topology(sibling, config, real_topology_definition)

    def __run(self):
        return super().__run()
