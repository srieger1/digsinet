import time
from apps.app import Application

from datetime import datetime

from event.eventbroker import EventBroker


class overview(Application):
    """Overview app"""

    cycle = dict()
    runEveryNCycles = 10

    def __init__(self, config, real_topo, logger, m_logger=None, load_increase=0):
        """Constructor"""
        super().__init__(config, real_topo, logger, m_logger, load_increase)

    async def run(self, topo: dict, broker: EventBroker, task: dict):
        """Run the overview app"""
        start_time = time.perf_counter()

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

            i = 0
            while i < (self.load_increase + 1):
                iteration_start_time = time.perf_counter()
                i += 1
                if topo_interfaces.get("gnmi"):
                    overview = topo_interfaces["gnmi"].getOverview(topo_nodes)
                    broker.publish("overview", {topology: overview})
                else:
                    self.logger.warning(
                        "No gNMI interface configured for topology " + topology + ", "
                        "skipping overview..."
                    )
                iteration_end_time = time.perf_counter()
                if (self.m_logger):
                    iteration_elapsed_time = iteration_end_time - iteration_start_time
                    self.m_logger.debug(f"Time taken to run single iteration of overview app for topology {topology}: {iteration_elapsed_time:.5f} seconds")
                

            end_time = time.perf_counter()
            if (self.m_logger):
                elapsed_time = end_time - start_time
                self.m_logger.debug(f"Time taken to run overview app for topology {topology}: {elapsed_time:.5f} seconds")

