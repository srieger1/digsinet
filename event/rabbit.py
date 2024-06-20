from typing import List

import pika
import json

from event.eventbroker import EventBroker
from logging import Logger
from pika import ConnectionParameters, PlainCredentials
from pika.exchange_type import ExchangeType
from config import RabbitSettings


class RabbitClient(EventBroker):
    def __init__(self, config: RabbitSettings, channels: List[str], logger: Logger):
        """
        Connects to the RabbitMQ Servers specified in config, declaring an exchange
        and creating a queue for each channel in channels.

        Attributes:
            config (RabbitSettings): Configuration object containing RabbitMQ settings
            channels (List[str]): List of channels to connect to
            logger (Logger): Logger for debug purposes
            conn_params (pika.ConnectionParameters): Connection parameters for RabbitMQ
            mq_chan (pika.Channel): The communication channel for interacting with RabbitMQ
        """
        super().__init__(config, channels, logger)
        self.config = config
        self.channels = channels
        self.logger = logger
        self.conn_params = ConnectionParameters(host=config.host, port=config.port,
                                                credentials=PlainCredentials(config.username, config.password, True))

        self._conn = pika.BlockingConnection(self.conn_params)
        self.mq_chan = self._conn.channel()
        self.mq_chan.confirm_delivery()

        self.mq_chan.exchange_declare(
            exchange='digsinet',
            exchange_type=ExchangeType.direct,
            passive=False,
            durable=True,
            auto_delete=False
        )

        for channel in self.channels:
            self.mq_chan.queue_declare(queue=channel, auto_delete=False)
            self.mq_chan.queue_bind(
                queue=channel,
                exchange='digsinet',
                routing_key=channel
            )

    def publish(self, channel: str, data):
        # TODO: Get rid of the nasty '<not serializable>' later down the line
        self.logger.info(f"Publishing message to topic {channel}: {json.dumps(data, default=lambda obj: '<not serializable>')}")
        self.mq_chan.basic_publish(
            exchange='digsinet',
            routing_key=channel,
            body=json.dumps(data, default=lambda obj: '<not serializable>'),
            mandatory=True
        )

    def poll(self, channel: str, timeout):
        pass

    def subscribe(self, channel: str, group_id: str = None):
        pass

    def get_sibling_channels(self):
        pass

    def new_sibling_channel(self, channel: str):
        pass

    def close(self):
        for channel in self.channels:
            self.mq_chan.queue_delete(queue=channel)
        self.mq_chan.exchange_delete(exchange='digsinet')
        self.mq_chan.close()
