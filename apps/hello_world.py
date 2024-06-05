from apps.app import Application

from datetime import datetime


class hello_world(Application):
    '''Hello World app'''
    def __init__(self, config, real_topo, logger):
        '''Constructor'''
        super().__init__(config, real_topo, logger)

    async def run(self, topo: dict, queues: dict, task: dict):
        '''Run the hello-world app'''
        topology = topo['name']
        topo_nodes = topo['nodes']
        topo_interfaces = topo['interfaces']

        # if the sibling is not running, don't run the hello-world app
        if topo['running'] is False:
            self.logger.debug(f"hello-world app not running for topology {topology} because the sibling is not running")
            return

        self.logger.debug(f"Running hello-world app for topology {topology}...")

        if task is not None:
            self.logger.debug(f"hello-world app got Task: {str(task)}, ignoring it as hello-world does not react on tasks...")
        else:
            # if we did not get a task, we are running the hello-world app as a periodic task)

            # for each node in the topology, set the description of Ethernet1 to "Hello World!" and a timestamp using gNMI
            if topo_nodes is not None and len(topo_nodes) > 0:
                for node in topo_nodes.items():
                    node_name = node[0]

                    test_message = f"Hello World! update for node {node[0]} in topology {topology} at " + \
                                   datetime.now().strftime("%H:%M:%S")
                    self.logger.debug(f"Setting interface description for Ethernet1 on node {node[0]} in topology "
                                      f"{topology} to: {test_message}")
                    data = [
                        (
                            "openconfig:interfaces/interface[name=Ethernet1]",
                            {"config": {"description": test_message}},
                        )
                    ]

                    if topo_interfaces.get('gnmi'):
                        topo_interfaces['gnmi'].set(topo_nodes, node_name, "update", data)
                    else:
                        self.logger.warning("No gNMI interface configured for topology " + topology + ", "
                                            "skipping gNMI update...")
