from logging import Logger
from controllers.controller import Controller
from config import Settings
from event.eventbroker import EventBroker


class te(Controller):
    def __init__(
        self,
        config: Settings,
        real_topology_definition: dict,
        real_nodes: dict,
        sibling: str,
        broker: EventBroker,
        logger,
        reconfigure_containers,
        topology_prefix: str,
        topology_name: str,
        m_logger: Logger = None,
        load_increase: int = 0,
    ):
        super().__init__(
            config,
            real_topology_definition,
            real_nodes,
            sibling,
            broker,
            logger,
            reconfigure_containers,
            topology_prefix,
            topology_name,
            m_logger,
            load_increase,
        )

    def name(self):
        return "te"

    def __build_topology(self, sibling, real_topology_definition):
        return super().__build_topology(sibling, real_topology_definition)

    def __run(self):
        return super().__run()
