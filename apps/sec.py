import time
from apps.app import Application

class sec(Application):
    '''ci app'''


    def __init__(self, config, real_topo):
        '''Constructor'''
        super().__init__(config, real_topo)


    async def run(self, topo: dict, queues: dict, task: dict):
        sibling = topo['name']
        self.logger.debug("Running sec app for sibling " + topo['name'] + "...")

        if task is not None:
            self.logger.debug("sec app got Task: " + str(task))
            if task['type'] == "run fuzzer":
                # run fuzzer
                duration = time.time() - task['timestamp']
                self.logger.info("Sibling " + sibling + " running fuzzer (after " + str(round(duration,2)) + "s)...")
                # get the task
                queues['continuous_integration'].put({"type": "fuzzer result", 
                                    "source": "sec", 
                                    "request_timestamp": task['timestamp'],
                                    "timestamp": time.time(),
                                    "data": ""})
