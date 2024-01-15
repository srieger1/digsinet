from apps.app import Application

class sec(Application):
    '''ci app'''


    def __init__(self):
        '''Constructor'''
        super().__init__()


    async def run(self, config, real_topo, sibling_topo, queues, task):
        logger = config['logger']

        logger.debug("Running sec app for sibling " + sibling_topo['name'] + "...")

        if task is not None:
            logger.debug("sec app got Task: " + str(task))
            if task['type'] == "run fuzzer":
                # run fuzzer
                logger.info("Running fuzzer...")
                # get the task
                queues['continuous_integration'].put({"type": "fuzzer result", 
                                    "source": "sec", 
                                    "data": ""})
