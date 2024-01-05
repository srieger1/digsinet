from controllers.controller import Controller


class te(Controller):
    def __init__(self, config, clab_topology_definition, sibling, real_nodes, queues):
        Controller.__init__(self, config, clab_topology_definition, sibling, real_nodes, queues)
        #TODO: check name of controller being set


    def name(self):
        return "te"


    def build_sibling(self, config, clab_topology_definition):
        return super().build_sibling(config, clab_topology_definition)
    
    
    def run(self):
        return super().run()