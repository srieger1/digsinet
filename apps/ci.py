async def run(config, clab_topology_definition, model, sibling, task):
    logger = config['logger']

    logger.debug("Running ci app for sibling " + sibling + "...")

    if task is not None:
        logger.debug("ci app got Task: " + str(task))

        if task['type'] == "gNMI notification":
            # if the gNMI data diff contains a value_change and the second item in the diff is fuzz_me
            if task['diff'].get('values_changed') and task['diff']['values_changed'].items[1].t2 == "fuzz_me":
                logger.info("gNMI data changed: " + str(task['diff']['values_changed']))
                # add task to queue for sec app
                model['queues']['security'].put({"type": "run fuzzer", 
                                "source": "ci", 
                                "data": ""})

        if task['type'] == "fuzzer result":
            logger.info("Got fuzzer result: " + task['data'])