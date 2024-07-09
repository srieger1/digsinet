import time
from typing import List
from config.kafka import KafkaSettings
from event.eventbroker import EventBroker
from logging import Logger
from confluent_kafka import Consumer, Producer
from confluent_kafka.admin import AdminClient, NewTopic
from message.kafka import KafkaMessage
from message.message import Message
import uuid
import json


class KafkaClient(EventBroker):
    def __init__(self, config: KafkaSettings, channels: List[str], logger: Logger):
        super().__init__(config, channels, logger)
        self.config = config
        self.logger = logger
        self.consumers = dict()
        self.producers = dict()
        self.admin = AdminClient(self.__createAdminConfig(config.host, config.port))
        self.kafka_topics = set(self.admin.list_topics().topics.keys())
        self.topics = channels
        for topic in self.topics:
            self.new_sibling_channel(topic)

    def publish(self, channel: str, data):
        if channel not in self.producers:
            self.logger.error(f"Producer for topic {channel} not found")
            self.__createProducer(channel)
        self.logger.info(
            f"Producing message to topic {channel}: {json.dumps(data, default= lambda obj: '<not serializable>')}"
        )
        self.producers[channel].produce(
            channel, json.dumps(data, default=lambda obj: "<not serializable>")
        )
        self.producers[channel].poll(1)

    def poll(self, consumer, timeout) -> Message:
        message = consumer.poll(timeout)
        if message is None:
            return None
        return KafkaMessage(message)

    def subscribe(self, channel: str, group_id: str = None):
        # TODO Alternative for single consumer groups (instead of using uuid)
        # Forcing unique group_id for each consumer
        group_id = group_id + "_" + uuid.uuid4().hex
        key = channel + "_" + group_id
        if key not in self.consumers:
            self.__createConsumer(group_id, channel)
        return self.consumers[channel + "_" + group_id], key

    def get_sibling_channels(self):
        return self.topics

    def __clear_all_channels(self):
        for topic in self.kafka_topics.copy():
            if topic == "__consumer_offsets":
                continue
            # Deletes the topic if it already exists
            # This is useful for testing purposes
            self.__delete_sibling_channel(topic)
            self.__wait_for_topic_deletion(topic)

    def __delete_sibling_channel(self, channel: str):
        if channel in self.kafka_topics:
            res = self.admin.delete_topics([channel], operation_timeout=10)
            for topic, f in res.items():
                try:
                    f.result()
                    self.kafka_topics.remove(channel)
                    self.logger.info(f"Topic {topic} marked for removal")
                except Exception as e:
                    self.logger.error(f"Failed to remove topic {topic}: {e}")

    def __wait_for_topic_deletion(self, topic: str, timeout: int = 10):
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                metadata = self.admin.list_topics(timeout=5)
                if topic not in metadata.topics.keys():
                    self.logger.info(f"Topic {topic} successfully deleted")
                    return
                self.logger.info(f"Waiting for topic {topic} to be deleted...")
            except Exception as e:
                self.logger.error(f"Error while waiting for topic deletion: {e}")
            time.sleep(1)
        self.logger.warning(f"Timeout reached. Topic {topic} may not be deleted.")

    def new_sibling_channel(self, channel: str):
        if channel not in self.kafka_topics:
            new_topic = NewTopic(
                channel,
                num_partitions=self.config.topics.num_partitions,
                replication_factor=self.config.topics.replication_factor,
            )
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

    def close(self):
        self.__close_all_consumers()
        self.__close_all_producers()
        self.__clear_all_channels()

    def closeConsumer(self, key: str):
        if key in self.consumers:
            self.consumers[key].unsubscribe()
            self.consumers[key].unassign()
            self.consumers[key].close()
            self.logger.info(f"Consumer for key {key} closed")
            del self.consumers[key]

    def __close_all_consumers(self):
        for consumer in self.consumers.values():
            try:
                consumer.close()
            except Exception as e:
                self.logger.error(f"Error while closing consumer: {e}")
            self.logger.info(f"Consumer {consumer} closed")
        self.consumers.clear()
        self.logger.info("All consumers closed")

    def __close_all_producers(self):
        for producer in self.producers.values():
            try:
                producer.purge()
                producer.flush()
            except Exception as e:
                self.logger.error(f"Error while closing producer: {e}")
            self.logger.info(f"Producer {producer} flushed")
        self.producers.clear()
        self.logger.info("All producers closed")

    def __createAdminConfig(self, host: str, port: int):
        return {
            "bootstrap.servers": f"{host}:{port}",
        }

    def __createConsumerConfig(self, group_id: str):
        # auto.offset.reset = "earliest" to read from the beginning of the topic
        # auto.offset.reset = "latest" to read from the end of the topic
        # Only works for new consumer groups, otherwise will use the last committed offset
        conf = {
            "bootstrap.servers": f"{self.config.host}:{self.config.port}",
            "group.id": group_id,
            "auto.offset.reset": self.config.offset.reset_type.value,
        }

        return conf

    def __createProducerConfig(self, client_id: str):
        conf = {
            "bootstrap.servers": f"{self.config.host}:{self.config.port}",
            "client.id": client_id,
        }

        return conf

    def __createConsumer(self, group_id: str, topic: str):
        if topic not in self.consumers:
            consumer = Consumer(self.__createConsumerConfig(group_id))
            consumer.subscribe([topic])
            self.consumers[topic + "_" + group_id] = consumer
            self.logger.info(f"Consumer in Group {group_id} created for topic {topic}")

        return self.consumers[topic + "_" + group_id]

    def __createProducer(self, client_id: str):
        if client_id not in self.producers:
            producer = Producer(self.__createProducerConfig(client_id))
            self.producers[client_id] = producer
            self.logger.info(f"Producer {client_id} created")
