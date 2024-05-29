import json
import uuid
from logging import Logger
from confluent_kafka import Consumer, Producer
from confluent_kafka.admin import AdminClient, NewTopic

class KafkaClient:
    def __init__(self, config: dict, logger: Logger, topics: list[str]):
        self.config = config
        self.logger = logger
        self.consumers = dict()
        self.producers = dict()
        self.admin = AdminClient(self.createAdminConfig(config["host"], config["port"]))
        self.kafka_topics = set(self.admin.list_topics().topics.keys())
        self.topics = topics
        for topic in topics:
            self.createTopic(topic)

    def createAdminConfig(self, host: str, port: int):
        conf = {
            "bootstrap.servers": f"{host}:{port}",
        }

        return conf
    
    def createConsumerConfig(self, group_id: str):
        # auto.offset.reset = "earliest" to read from the beginning of the topic
        # auto.offset.reset = "latest" to read from the end of the topic
        # Only works for new consumer groups, otherwise will use the last committed offset
        conf = {
            "bootstrap.servers": f"{self.config['host']}:{self.config['port']}",
            "group.id": group_id,
            "auto.offset.reset": "earliest",
        }

        return conf
    
    def createProducerConfig(self, client_id: str):
        conf = {
            "bootstrap.servers": f"{self.config['host']}:{self.config['port']}",
            "client.id": client_id,
        }

        return conf
    
    def __createConsumer(self, group_id: str, topic: str):
        if topic not in self.consumers:
            consumer = Consumer(self.createConsumerConfig(group_id))
            consumer.subscribe([topic])
            self.consumers[topic + "_" + group_id] = consumer
            self.logger.info(f"Consumer in Group {group_id} created for topic {topic}")

        return self.consumers[topic + "_" + group_id]

    def createProducer(self, client_id: str):
        if client_id not in self.producers:
            producer = Producer(self.createProducerConfig(client_id))
            self.producers[client_id] = producer
            self.logger.info(f"Producer {client_id} created")

    def createTopic(self, topic: str):
        if topic not in self.kafka_topics:
            new_topic = NewTopic(topic, num_partitions=self.config["topics"]["num_partitions"], replication_factor=self.config["topics"]["replication_factor"])
            res = self.admin.create_topics(
                new_topics=[new_topic], validate_only=False, operation_timeout=10
            )
            for topic, f in res.items():
                try:
                    f.result()
                    self.kafka_topics.add(topic)
                    self.logger.info(f"Topic {topic} created")
                except Exception as e:
                    self.logger.error(f"Failed to create topic {topic}: {e}")

    def getTopics(self):
        return self.topics

    def getConsumer(self, group_id: str, topic: str):
        # TODO Alternative for single consumer groups (instead of using uuid)
        # Forcing unique group_id for each consumer
        group_id = group_id + "_" + uuid.uuid4().hex
        key = topic + "_" + group_id
        if key not in self.consumers:
            self.__createConsumer(group_id, topic)
        return self.consumers[topic + "_" + group_id]
    
    def closeConsumer(self, topic: str):
        if topic in self.consumers:
            self.consumers[topic].close()
            self.logger.info(f"Consumer for topic {topic} closed")
            del self.consumers[topic]

    def closeAllConsumers(self):
        for topic in self.consumers:
            self.closeConsumer(topic)

    def put(self, topic: str, value):
        if (topic not in self.producers):
            self.logger.error(f"Producer for topic {topic} not found")
            self.createProducer(topic)
        # self.logger.info(f"Converted value to JSON: {value}")
        self.logger.info(f"Producing message to topic {topic}: {json.dumps(value, default= lambda obj: '<not serializable>')}")
        self.producers[topic].produce(topic, json.dumps(value, default= lambda obj: '<not serializable>'))
        # self.logger.info(f"Produced message to topic {topic}")
        self.producers[topic].poll(1)
