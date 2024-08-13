import time
from apps.app import Application
from event.eventbroker import EventBroker


class sec(Application):
    """ci app"""

    def __init__(self, config, real_topo, logger):
        """Constructor"""
        super().__init__(config, real_topo, logger)

    async def run(self, topo: dict, broker: EventBroker, task: dict):
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
