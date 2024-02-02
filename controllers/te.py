from controllers.controller import Controller


class te(Controller):
    def __init__(self, config: dict, real_topology_definition: dict, real_nodes: dict, sibling: str, queues: dict):
        super().__init__(config, real_topology_definition, real_nodes, sibling, queues)


    def name(self):
        return "te"


    def __build_topology(self, sibling, config, real_topology_definition):
        return super().__build_topology(sibling, config, real_topology_definition)
    
    
    def __run(self):
        return super().__run()