from typing import List

import pika
import json

from event.eventbroker import EventBroker
from logging import Logger
from pika import ConnectionParameters, PlainCredentials
from pika.exchange_type import ExchangeType
from config import RabbitSettings
from message.message import Message


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

        self._connection = None
        self.mq_chan = None
        self.is_consuming = True
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

    def __connect(self):
        self.logger.info('Connecting to RabbitMQ at %s:%d', self.conn_params.host, self.conn_params.port)
        self._connection = pika.SelectConnection(
            parameters=self.conn_params,
            on_open_callback=self.__on_connection_open
        )

    def __on_connection_open(self, _unused_connection):
        self.logger.info('Connection to RabbitMQ has been opened')
        self.__open_channel()


    def __open_channel(self):
        self.logger.info('Creating new RabbitMQ channel')
        self._connection.channel(on_open_callback=self.__on_open_channel)


    def __on_open_channel(self, channel):
        self.logger.info('Channel opened')
        self.mq_chan = channel
        self.mq_chan.add_on_close_callback(self.__on_channel_closed)

    def __on_channel_closed(self, channel, reason):
        self.logger.warning('Channel %i was closed. Reason: %s', channel, reason)
        self.close()


    def publish(self, channel: str, data):
        # TODO: Get rid of the nasty '<not serializable>' later down the line
        self.logger.info(f"Publishing message to topic {channel}: {json.dumps(data, default=lambda obj: '<not serializable>')}")
        self.mq_chan.basic_publish(
            exchange='digsinet',
            routing_key=channel,
            body=json.dumps(data, default=lambda obj: '<not serializable>'),
            mandatory=True
        )

    def poll(self, consumer, timeout) -> Message:
        pass

    def subscribe(self, channel: str, group_id: str = None):
        pass

    def get_sibling_channels(self):
        return self.channels

    def new_sibling_channel(self, channel: str):
        if channel not in self.channels:
            self.logger.info(f"Creating new channel {channel}...")
            self.mq_chan.queue_declare(queue=channel, auto_delete=False)
            self.mq_chan.queue_bind(
                queue=channel,
                exchange='digsinet',
                routing_key=channel
            )
            self.logger.info(f"Successfully created new channel {channel}...")

    def close(self):
        self.is_consuming = False
        if self._connection.is_closing or self._connection.is_closed:
            self.logger.info('Connection already closed')
        else:
            self._connection.close()
