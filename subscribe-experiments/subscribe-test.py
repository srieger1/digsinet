import os
import json

from pygnmi.client import gNMIclient, telemetryParser

ARISTA_HOST = os.getenv("ARISTA_HOST", "clab-realnet_security-ceos1")
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
        {
            'path': '/',
            'mode': 'on_change',
        },             
        #{
        #    'path': 'openconfig:interfaces/interface/state',
        #    'mode': 'on_change',
        #},             
        #{
        #    'path': 'openconfig:interfaces/interface/subinterfaces/subinterface',
        #    'mode': 'on_change',
        #},
    ],
    "mode": "stream",
    "encoding": "json",
}

with gNMIclient(
    target=host, username=ARISTA_USERNAME, password=ARISTA_PASSWORD, insecure=True
) as gc:
    telemetry_stream = gc.subscribe(subscribe=subscribe)
    for telemetry_entry in telemetry_stream:
        telemetry_data = telemetryParser(telemetry_entry)
        if telemetry_data.get("update"):
            if telemetry_data.get("update").get("update"):
                path =  telemetry_data.get("update").get("update")[0].get("path")
                if path == "interfaces/interface[name=Ethernet1]/config/mtu":
                    print(path + ":\n" + json.dumps(telemetry_data, indent = 4))
                else:
                    print(path)
                    print(telemetry_data)
