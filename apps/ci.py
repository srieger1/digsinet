from apps.app import Application
import time

from event.eventbroker import EventBroker


class ci(Application):
    """ci app"""

    def __init__(self, config, real_topo, logger):
        """Constructor"""
        super().__init__(config, real_topo, logger)

    async def run(self, topo: dict, broker: EventBroker, task: dict):
        sibling = topo["name"]
        self.logger.debug(f"Running ci app for sibling {sibling}...")

        if task is not None:
            self.logger.debug("ci app got Task: " + str(task))

            if task["type"] == "gNMI notification" and task["source"] == "realnet":
                # if the gNMI data diff contains a value_change
                # and the second item in the diff is fuzz_me
                if (
                    task.get("diff")
                    and task["diff"].get("values_changed")
                    and task["diff"]["values_changed"].items[1].t2 == "fuzz_me"
                ):
                    self.logger.info(
                        f"Sibling {sibling} detected gNMI "
                        f"notification 'fuzz_me', asking sec"
                        "app to run fuzzer..."
                    )
                    # add task to queue for sec app
                    broker.publish(
                        "security",
                        {
                            "type": "run fuzzer",
                            "source": "ci",
                            "timestamp": time.time(),
                            "data": "",
                        },
                    )

            if task["type"] == "fuzzer result":
                duration = time.time() - task["request_timestamp"]
                self.logger.info(
                    f"Sibling {sibling} got fuzzer result"
                    f" after {str(round(duration, 2))}s: {task['data']}"
                )
