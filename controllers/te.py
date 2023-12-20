from controllers.controller import Controller

class te(Controller):
    def __init__(self, config, clab_topology_definition, model, sibling):
        Controller.__init__(self, config, clab_topology_definition, model, sibling)
        #TODO: check name of controller being set
        self.name = "te"
    
    def run(self):
        return super().run()