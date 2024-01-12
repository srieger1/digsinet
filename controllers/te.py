from controllers.controller import Controller


class te(Controller):
    def __init__(self, config, real_topology_definition, real_nodes, queues):
        Controller.__init__(self, config, real_topology_definition, real_nodes, queues)
        #TODO: check name of controller being set


    def name(self):
        return "te"


    def build_sibling(self, sibling, config, real_topology_definition):
        return super().build_sibling(sibling, config, real_topology_definition)
    
    
    def run(self):
        return super().run()