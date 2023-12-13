import asyncio
import multiprocessing

import importlib

class Controller(multiprocessing.Process):
    def __init__(self, config, clab_topology_definition, model, sibling):
        multiprocessing.Process.__init__(self)
        multiprocessing.current_process().daemon = False
        multiprocessing.current_process().name = "Controller for " + sibling
        multiprocessing.Process.start(self)

        self.config = config
        self.clab_topology_definition = clab_topology_definition
        self.model = model
        self.sibling = sibling
        self.apps = dict()
        self.name = "controller base class"

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

    def run(self):
        # run controller apps
        # for sibling in model['siblings']:
        #     if model['siblings'][sibling].get('running'):
        #         print("=== Run Controller for " + sibling + "...")
        #         # get controller for sibling and its apps and run them
        #         for app in config['controllers'][config['siblings'][sibling]['controller']]['apps']:
        #             # parallelized execution is suboptimal for now
        #             asyncio.run(model['apps'][app].run(config, clab_topology_definition, model, sibling))
        #             # model['apps'][app].run(config, clab_topology_definition, model, sibling)

        # get controller for sibling and its apps and run them
        for app in self.apps:
            # parallelized execution is suboptimal for now
            print("=== Running App " + app + " on Controller " + self.name + " for sibling " + self.sibling + "...")
            asyncio.run(self.apps[app].run(self.config, self.clab_topology_definition, self.model, self.sibling))
            # self.apps[app].run(self.config, self.clab_topology_definition, self.model, self.sibling)