from apps.app import Application

class sec(Application):
    '''ci app'''


    def __init__(self):
        '''Constructor'''


    async def run(self, config, clab_topology_definition, sibling, sibling_clab_topo, real_nodes, queues, task):
        logger = config['logger']

        logger.debug("Running sec app for sibling " + sibling + "...")

        if task is not None:
            logger.debug("sec app got Task: " + str(task))
            if task['type'] == "run fuzzer":
                # run fuzzer
                logger.info("Running fuzzer...")
                # get the task
                queues['continuous_integration'].put({"type": "fuzzer result", 
                                    "source": "sec", 
                                    "data": ""})
