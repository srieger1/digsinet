import json
import os
import time
from datetime import datetime

from pygnmi.client import gNMIclient, telemetryParser

from multiprocessing import Process, Queue

from confluent_kafka import Producer, Consumer

from prometheus_client import start_http_server, Gauge

def telemetryHandler(host: str, mode: str = "subscribe", queue: Queue = None):

    def acked(err, msg):
        if err is not None:
            print("Failed to deliver message: %s: %s" % (str(msg), str(err)))
        #else:
        #    print("Message produced: %s" % (str(msg)))

    kafka_host = "localhost:29092"

    producer_conf = {
        'bootstrap.servers': kafka_host,
        'client.id': 'python-producer-' + host,
    }
    consumer_conf = {
        'bootstrap.servers': kafka_host,
        'client.id': 'python-consumer-' + host,
        'group.id': 'python-consumer',
        'auto.offset.reset': 'earliest'
    }

    topics = ["realnet", "security", "continuous_integration"]

    producer = Producer(producer_conf)
    consumer = Consumer(consumer_conf)
    consumer.subscribe(topics)

    #ARISTA_HOST = os.getenv("ARISTA_HOST", "clab-realnet-ceos1")
    ARISTA_PORT = os.getenv("ARISTA_PORT", "6030")
    ARISTA_USERNAME = os.getenv("ARISTA_USERNAME", "admin")
    ARISTA_PASSWORD = os.getenv("ARISTA_PASSWORD", "admin")

    targetHost = (host, ARISTA_PORT)

    poll_delay = 1

    poll_paths = [
        {
            "path": "/",
            "datatype": "operational",
            "encoding": "json",
        },
        #{
        #    "path": "network-instances",
        #    "datatype": "all",
        #    "encoding": "json",
        #},
        #{
        #    "path": "network-instances/network-instance/protocols/protocol/bgp/neighbors/neighbor",
        #    "datatype": "all",
        #    "encoding": "json",
        #},
    ]

    subscribe = {
        "subscription": [
            {
                "path": "/",
                #"mode": "sample",
                "mode": "on_change",
                # minimum 2ms: ~7000 notifications per second
                #"sample_interval": 2000000,
                # 1s: ~3300 notifications per second
                "sample_interval": 1000000000,
                # 10s: ~3300 notifications per second
                #"sample_interval": 10000000000,
            },
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
            #{
            #    'path': 'openconfig:interfaces/interface/subinterfaces/subinterface/ipv4',
            #    'mode': 'on_change',
            #},             
        ],
        "mode": "stream",
        "encoding": "json",
    }

    startime = time.time()
    samples = 0
    bytes = 0

    with gNMIclient(
        target=targetHost, username=ARISTA_USERNAME, password=ARISTA_PASSWORD, insecure=True
    ) as gc:
        if mode == "subscribe":
            telemetry_stream = gc.subscribe(subscribe=subscribe)
            for telemetry_entry in telemetry_stream:
                telemetry_data = telemetryParser(telemetry_entry)
                sampletime = time.time()
                if telemetry_data.get("update"):
                    if telemetry_data.get("update").get("update"):
                        samples += len(telemetry_data.get("update").get("update"))
                    elif telemetry_data.get("update").get("delete"):
                        samples += len(telemetry_data.get("update").get("delete"))
                    else:
                        print("no update or delete in update")
                        samples += 1
                elif telemetry_data.get("sync_response"):
                    samples += 1
                else:
                    print("no update or sync_response")
                    samples += 1
                bytes = bytes + len(json.dumps(telemetry_data, indent=2))
                if sampletime - startime > 1:

                    #message = consumer.poll(1)
                    #if message is not None:
                    #    if message.error():
                    #        print("Consumer error: {}".format(message.error()))
                    #    #else:
                    #    #    print("Received message: {}".format(message.value().decode('utf-8')))
        
                    print(datetime.now().strftime("%H:%M:%S") + " " + host + ":" + str(samples) + " samples/s, " + str(bytes) + " bytes JSON")
                    #print(len(telemetry_data))

                    # send data to queue
                    msg = {
                        "host": host,
                        "samples_per_second": samples,
                        "bytes_per_second": bytes,
                    }
                    queue.put(msg)

                    startime = sampletime
                    samples = 0
                    bytes = 0

                for topic in topics:
                    producer.produce(topic, json.dumps(telemetry_data, indent=2), callback=acked)
                    #producer.poll(1)
                #print(json.dumps(telemetry_data, indent=2))
        elif mode == "poll":
            while True:
                for poll_path in poll_paths:
                    telemetry_data = gc.get(path=[poll_path["path"]], datatype=poll_path["datatype"], encoding=poll_path["encoding"])
                    sampletime = time.time()
                    samples += 1
                    bytes = bytes + len(json.dumps(telemetry_data, indent=2))
                    if sampletime - startime > 1:

                        #message = consumer.poll(1)
                        #if message is not None:
                        #    if message.error():
                        #        print("Consumer error: {}".format(message.error()))
                        #    #else:
                        #    #    print("Received message: {}".format(message.value().decode('utf-8')))

                        print(datetime.now().strftime("%H:%M:%S") + " " + host + ":" + str(samples) + " samples/s, " + str(bytes) + " bytes JSON")
                        #print(len(telemetry_data))

                        # send data to queue
                        msg = {
                            "host": host,
                            "samples_per_second": samples,
                            "bytes_per_second": bytes,
                        }
                        queue.put(msg)

                        startime = sampletime
                        samples = 0
                        bytes = 0

                    for topic in topics:
                        producer.produce(topic, json.dumps(telemetry_data, indent=2), callback=acked)
                        #producer.poll(1)
                    #print(json.dumps(telemetry_data, indent=2))

                time.sleep(poll_delay)

def main():

    # define prometheus metrics
    start_http_server(8001)
    g = Gauge('gnmi_sample', 'gNMI benchmark sample', ['host','type'])

    hosts = ["clab-realnet-ceos1", "clab-realnet-ceos2", "clab-realnet_security-ceos1", "clab-realnet_continuous_integration-ceos1", "clab-realnet_continuous_integration-ceos3"]
    #mode = "subscribe"
    mode = "poll"

    queue = Queue()

    for host in hosts:
        telemetryHandlerProcess = Process(target=telemetryHandler, args=(host,mode,queue,), name="telemetryHandler-"+host)
        telemetryHandlerProcess.start()

    while True:
        if not queue.empty():
            msg = queue.get(timeout=1)
            if msg is not None:
                # send data to prometheus
                g.labels(msg["host"], "samples_per_second").set(float(msg["samples_per_second"]))
                g.labels(msg["host"], "bytes_per_second").set(float(msg["bytes_per_second"]))
                g.labels(msg["host"], "sample").inc()

if __name__ == "__main__":
    main()