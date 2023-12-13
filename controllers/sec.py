from controllers.controller import Controller

class sec(Controller):
    def __init__(self, config, clab_topology_definition, model, sibling):
        Controller.__init__(self, config, clab_topology_definition, model, sibling)
        self.name = "Controller " + __name__ + " for sibling " + sibling
    
    def runApps(self):
        return super().runApps()