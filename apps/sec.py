async def run(config, clab_topology_definition, model, sibling, task):
    logger = config['logger']

    logger.debug("Running sec app for sibling " + sibling + "...")

    if task is not None:
        logger.debug("sec app got Task: " + str(task))
        if task['type'] == "run fuzzer":
            # run fuzzer
            logger.info("Running fuzzer...")
            # get the task
            model['queues']['continuous_integration'].put({"type": "fuzzer result", 
                                "source": "sec", 
                                "data": ""})
