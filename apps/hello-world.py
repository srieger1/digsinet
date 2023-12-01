from datetime import datetime
from pygnmi.client import gNMIclient

async def run(config, clab_topology_definition, model, sibling):
    port = config['gnmi']['port']
    username = config['gnmi']['username']
    password = config['gnmi']['password']

    # assume same nodes in each sibling as in real network for now
    for node in clab_topology_definition['topology']['nodes'].items():
        # assume clab as the default prefix for now
        host = "clab-" + clab_topology_definition['name'] + "_" + sibling + "-" + node[0]
        with gNMIclient(target=(host, port), username=username, password=password, insecure=True) as gc:
            print("Hello World! for sibling " + sibling + " at " + datetime.now().strftime("%H:%M:%S"))
            description = "Hello World! for sibling " + sibling + " at " + datetime.now().strftime("%H:%M:%S")
            result = gc.set(update=[("openconfig:interfaces/interface[name=Ethernet1]", {"config": {"description": description}})])
            # print("gNMI interface desc set for Ethernet1")
