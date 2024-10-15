import json
import socket
import time

from event.eventbroker import EventBroker
from logging import Logger
from config import RabbitSettings
from message.rabbit import RabbitMessage
from typing import List, Dict
from kombu import Connection, Queue, Exchange, Consumer, Message, Producer


class RabbitConsumer:
    def __init__(
        self,
        logger: Logger,
        conn: Connection,
        queue: Queue,
        exchange: Exchange,
    ):
        self.logger = logger
        self.conn = conn
        self.queue = queue
        self.exchange = exchange
        self.consumer = Consumer(conn, [queue], on_message=self.__on_message)
        self.consumer.consume()
        self.messages = []

    def __on_message(self, message: Message):
        self.logger.info(f"received message from rabbit: {message}")
        self.messages.append(message)
        message.ack()

    def has_messages(self):
        return len(self.messages) > 0

    def poll(self, timeout) -> RabbitMessage:
        self.logger.info(f"Polling {self.queue.name}...")
        time_start = time.monotonic()
        remaining = timeout
        while True:
            if len(self.messages) > 0:
                return RabbitMessage(self.messages.pop(0).body)

            if remaining is not None and remaining <= 0.0:
                return None
            try:
                self.conn.drain_events(timeout=remaining)
            except socket.timeout:
                self.logger.warning("exceeded timeout while waiting for message")
                return None
            # TODO: This is very strange,
            #  definitely needs to be addressed later down the line
            except OSError:
                return None

            if remaining is not None:
                elapsed = time.monotonic() - time_start
                remaining = timeout - elapsed

    def close(self):
        self.consumer.close()
        self.conn.release()


class RabbitClient(EventBroker):
    def __init__(self, config: RabbitSettings, channels: List[str], logger: Logger):
        super().__init__(config, channels, logger)
        self.config = config
        self.channels = channels
        self.logger = logger
        self.exchange = Exchange(name="digsinet", type="direct", durable=True)
        self.queues: List[Queue] = []
        for channel in self.channels:
            queue = Queue(channel, exchange=self.exchange, routing_key=channel)
            self.queues.append(queue)
        self.consumers: Dict[str, RabbitConsumer] = {}

    def __make_connection(self) -> Connection:
        return Connection(
            hostname=self.config.host,
            userid=self.config.username,
            password=self.config.password,
            port=self.config.port,
            heartbeat=10.0,
        )

    def close(self):
        for consumer in self.consumers.values():
            consumer.close()

    def close_consumer(self, consumer: str):
        if consumer in self.consumers:
            self.consumers[consumer].close()
            del self.consumers[consumer]

    def get_sibling_channels(self):
        return self.channels

    def new_sibling_channel(self, channel: str):
        queue = Queue(channel, exchange=self.exchange, routing_key=channel)
        self.queues.append(queue)

    def subscribe(self, channel: str, group_id: str = None):
        queue = Queue(channel, exchange=self.exchange, routing_key=channel)
        self.logger.info(f"Subscribing to channel {channel}")
        conn = self.__make_connection()
        print(queue.name)
        print(self.exchange)
        consumer = RabbitConsumer(self.logger, conn, queue, self.exchange)
        self.consumers[channel] = consumer
        return channel, channel

    def poll(self, consumer, timeout) -> RabbitMessage:
        if consumer in self.consumers:
            if self.consumers[consumer].has_messages():
                return self.consumers[consumer].messages.pop(0)
            else:
                return self.consumers[consumer].poll(timeout)
        else:
            self.logger.warning("poll attempted for non existing consumer")
            return RabbitMessage("")

    def publish(self, channel: str, data):
        self.logger.info(f"Publishing message to channel {channel}...")
        conn = self.__make_connection()
        producer = Producer(conn)
        producer.publish(
            json.dumps(data, default=lambda obj: "<not serializable>"),
            exchange=self.exchange,
            routing_key=channel,
            retry=True,
            declare=self.queues,
        )
        self.logger.info(f"Published message to channel {channel}...")
        producer.close()
        conn.release()
