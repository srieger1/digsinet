import os
import time

from pygnmi.client import gNMIclient, telemetryParser

ARISTA_HOST = os.getenv("ARISTA_HOST", "clab-realnet-ceos1")
ARISTA_PORT = os.getenv("ARISTA_PORT", "6030")
ARISTA_USERNAME = os.getenv("ARISTA_USERNAME", "admin")
ARISTA_PASSWORD = os.getenv("ARISTA_PASSWORD", "admin")

host = (ARISTA_HOST, ARISTA_PORT)

while True:
    #update = [
    #    (
    #        "openconfig:/interfaces/interface[name=Ethernet1]",
    #        {"config": {"description": "gNMI PING " + str(time.monotonic_ns())}},
    #    )
    #]
    update = [
        (
            "openconfig:/interfaces/interface[name=Ethernet1]",
            {"config": {"description": "gNMI PING " + str(time.time())}},
        )
    ]

    with gNMIclient(
        target=host, username=ARISTA_USERNAME, password=ARISTA_PASSWORD, insecure=True
    ) as gc:
        telemetry_stream = gc.set(update=update)
    time.sleep(1)