from controllers.controller import Controller
from queues.client import MessageQueueClient


class te(Controller):
    def __init__(self, config: dict, real_topology_definition: dict, real_nodes: dict, sibling: str, mq_client: MessageQueueClient):
        super().__init__(config, real_topology_definition, real_nodes, sibling, mq_client)

    def name(self):
        return "te"

    def __build_topology(self, sibling, config, real_topology_definition):
        return super().__build_topology(sibling, config, real_topology_definition)

    def __run(self):
        return super().__run()
