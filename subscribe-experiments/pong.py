import os
import time

from pygnmi.client import gNMIclient, telemetryParser

ARISTA_HOST = os.getenv("ARISTA_HOST", "clab-realnet-ceos1")
ARISTA_PORT = os.getenv("ARISTA_PORT", "6030")
ARISTA_USERNAME = os.getenv("ARISTA_USERNAME", "admin")
ARISTA_PASSWORD = os.getenv("ARISTA_PASSWORD", "admin")

host = (ARISTA_HOST, ARISTA_PORT)

subscribe = {
    "subscription": [
        #{
        #    "path": "/",
        #    "mode": "sample",
        #    "sample_interval": 10000000,
        #},
        #{
        #    "path": "interfaces/interface[name=Ethernet1]/state/counters",
        #    "mode": "sample",
        #    "sample_interval": 10000000000,
        #},
        #{
        #    "path": "network-instances/network-instance/protocols/protocol/bgp/neighbors/neighbor/state",
        #    "mode": "sample",
        #    "sample_interval": 10000000000,
        #},
        #{
        #    'path': '/interfaces/interface[name=Ethernet1]/state/oper-status',
        #    'mode': 'on_change',
        #},
        #{
        #    'path': '/interfaces/interface[name=Ethernet1]/*/config',
        #    'mode': 'on_change',
        #},             
        #{
        #    'path': '/',
        #    'mode': 'on_change',
        #},             
        #{
        #    'path': 'openconfig:interfaces/interface/state',
        #    'mode': 'on_change',
        #},             
        {
            'path': 'openconfig:interfaces/interface[name=Ethernet1]/config/description',
            'mode': 'on_change',
        },             
    ],
    "mode": "stream",
    "encoding": "json",
}

ewma = 0

with gNMIclient(
    target=host, username=ARISTA_USERNAME, password=ARISTA_PASSWORD, insecure=True
) as gc:
    telemetry_stream = gc.subscribe(subscribe=subscribe)
    for telemetry_entry in telemetry_stream:
        telemetry_data = telemetryParser(telemetry_entry)
        if telemetry_data.get("update"):
            if telemetry_data.get("update").get("update"):
                update_data = telemetry_data.get("update").get("update")[0]
                path = update_data.get("path")
                val = update_data.get("val")
                if path == "interfaces/interface[name=Ethernet1]/config/description":
                    val_components = val.split(" ")
                    if val_components[0] == "gNMI" and val_components[1] == "PING":
                        rtt = (time.monotonic_ns()-int(val_components[2])) / 1000000000
                        #print("Ping received on path: " + path + " with data: " + val + " RTT: " + str(rtt))
                        # print current time, received time, and RTT in seconds
                        ewma = 0.9 * ewma + 0.1 * rtt
                        print("current: " + str(time.monotonic_ns()) + " received: " + val_components[2] + " RTT: " + str(rtt) + " EWMA: " + str(ewma))
                    else:
                        print("Pong ignored path: " + path + " with data: ")
                        print(val)

                else:
                    print("Pong ignored path: " + path + " with data: ")
                    print(telemetry_data)
