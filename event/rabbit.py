import json
import time

from event.eventbroker import EventBroker
from logging import Logger
from config import RabbitSettings
from message.rabbit import RabbitMessage
from typing import List, Dict
from kombu import Connection, Queue, Exchange, Consumer, Message


class RabbitClient(EventBroker):
    def __init__(self, config: RabbitSettings, channels: List[str], logger: Logger):
        super().__init__(config, channels, logger)
        self.config = config
        self.channels = channels
        self.logger = logger
        self.connection = Connection(hostname=self.config.host, userid=self.config.username,
                                     password=self.config.password, port=self.config.port)
        self.exchange = Exchange(name='digsinet', type='direct', durable=True)
        self.queues: List[Queue] = []
        self.buffers: Dict[str, List[Message]] = {}
        for channel in self.channels:
            queue = Queue(channel, exchange=self.exchange, routing_key=channel)
            self.queues.append(queue)

        self.consumer = Consumer(channel=self.connection.channel(), no_ack=True,auto_declare=True,
                                 on_message=self.__on_message)
        self.producer = self.connection.Producer()

    def __on_message(self, message: Message):
        if message.delivery_info['routing_key'] in self.buffers.keys():
            self.buffers[message.delivery_info['routing_key']].append(message.body)
        else:
            self.logger.warning(f'Received Message for unknown Queue {message.delivery_info['routing_key']}')

    def close(self):
        self.connection.close()

    def close_consumer(self, consumer: str):
        if self.consumer.consuming_from(consumer):
            self.consumer.cancel_by_queue(consumer)

    def get_sibling_channels(self):
        return self.channels

    def new_sibling_channel(self, channel: str):
        queue = Queue(channel, exchange=self.exchange, routing_key=channel)
        self.queues.append(queue)

    def subscribe(self, channel: str, group_id: str = None):
        if not self.consumer.consuming_from(channel):
            self.consumer.add_queue(channel)
            self.consumer.consume()
        return channel, channel

    def poll(self, consumer, timeout) -> RabbitMessage:
        time_start = time.monotonic()
        remaining = timeout
        while True:
            if self.buffers[consumer]:
                return RabbitMessage(self.buffers[consumer].pop(0))

            if remaining is not None and remaining <= 0.0:
                return RabbitMessage('')

            self.connection.drain_events(timeout=remaining)

            if remaining is not None:
                elapsed = time.monotonic() - time_start
                remaining = timeout - elapsed

    def publish(self, channel: str, data):
        self.producer.publish(
            json.dumps(data, default=lambda obj: "<not serializable>"),
            exchange=self.exchange,
            routing_key=channel,
            declare=self.exchange
        )