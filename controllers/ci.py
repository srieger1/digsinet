from controllers.controller import Controller

class ci(Controller):
    def __init__(self, config, clab_topology_definition, model, sibling):
        Controller.__init__(self, config, clab_topology_definition, model, sibling)
        self.name = "ci"

    def run(self):
        return super().run()