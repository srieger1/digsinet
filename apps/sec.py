import time
from apps.app import Application
from event.eventbroker import EventBroker


class sec(Application):
    """ci app"""

    def __init__(self, config, real_topo, logger, m_logger=None, load_increase=0):
        """Constructor"""
        super().__init__(config, real_topo, logger, m_logger, load_increase)

    async def run(self, topo: dict, broker: EventBroker, task: dict):
        start_time = time.perf_counter()
        sibling = topo["name"]
        self.logger.debug(f"Running sec app for sibling {topo['name']}...")

        if task is not None:
            self.logger.debug("sec app got Task: " + str(task))
            if task["type"] == "run fuzzer":
                # run fuzzer
                duration = time.time() - task["timestamp"]
                self.logger.info(
                    f"Sibling {sibling} running fuzzer (after {str(round(duration, 2))}s)..."
                )
                # get the task
                broker.publish(
                    "continuous_integration",
                    {
                        "type": "fuzzer result",
                        "source": "sec",
                        "request_timestamp": task["timestamp"],
                        "timestamp": time.time(),
                        "data": "",
                    },
                )

                end_time = time.perf_counter()
                if (self.m_logger):
                    elapsed_time = end_time - start_time
                    self.m_logger.debug(f"Time taken to run sec app for topology {topo['name']}: {elapsed_time:.5f} seconds")
