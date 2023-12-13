import asyncio
from multiprocessing import Process

import importlib

class Controller():
    apps = dict()

    def __init__(self, config, clab_topology_definition, model, sibling):
        self.name = "Controller " + __name__ + " for sibling " + sibling
        self.daemon = False
        self.target = self.runApps
        self.start()
        print("Process id: " + str(self.pid))
        self.join()

        self.config = config
        self.clab_topology_definition = clab_topology_definition
        self.model = model
        self.sibling = sibling
        self.apps = dict()

        # import apps
        for app in config['apps']:
            # if app is used by controller in config
            if config['controllers'][config['siblings'][sibling]['controller']].get('apps'):
                if app in config['controllers'][config['siblings'][sibling]['controller']]['apps']:
                    self.import_app(app, config['apps'][app]['module'])

    def import_app(self, app, module):
        # import the module
        print("Loading app " + app + " for controller " + __name__ + "...")
        self.apps[app] = importlib.import_module(module)

    def runApps(self):
        # get controller for sibling and its apps and run them
        for app in self.apps:
            # parallelized execution is suboptimal for now
            print("=== Running App " + app + " on Controller " + self.name + " for sibling " + self.sibling + "...")
            asyncio.run(self.apps[app].run(self.config, self.clab_topology_definition, self.model, self.sibling))
            # self.apps[app].run(self.config, self.clab_topology_definition, self.model, self.sibling)
