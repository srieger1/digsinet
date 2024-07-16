from apps.app import Application

from datetime import datetime

from event.eventbroker import EventBroker


class overview(Application):
    """Overview app"""

    cycle = dict()
    runEveryNCycles = 10

    def __init__(self, config, real_topo, logger):
        """Constructor"""
        super().__init__(config, real_topo, logger)

    async def run(self, topo: dict, broker: EventBroker, task: dict):
        """Run the overview app"""

        topology = topo["name"]
        topo_nodes = topo["nodes"]
        topo_interfaces = topo["interfaces"]

        # if the sibling is not running, don't run the overview app
        if topo["running"] is False:
            self.logger.info(
                f"overview app not running for topology {topology} because the sibling is not running"
            )
            return

        self.logger.info(f"Running overview app for topology {topology}...")

        if task is not None:
            self.logger.info(
                f"overview app got Task: {str(task)}, ignoring it as overview does not react on tasks..."
            )
        else:
            # As the overview app is a periodic app, we only run it every N cycles to reduce unnecessary load
            if topo["name"] not in self.cycle:
                self.cycle[topo["name"]] = 0

            if (self.cycle[topo["name"]] % self.runEveryNCycles) != 0:
                self.cycle[topo["name"]] += 1
                return

            self.cycle[topo["name"]] = 1

            if topo_interfaces.get("gnmi"):
                overview = topo_interfaces["gnmi"].getOverview(topo_nodes)
                broker.publish("overview", {topology: overview})
            else:
                self.logger.warning(
                    "No gNMI interface configured for topology " + topology + ", "
                    "skipping overview..."
                )
