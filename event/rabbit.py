from typing import List

import pika
import json
import functools
import uuid
import time

from event.eventbroker import EventBroker
from logging import Logger
from pika import ConnectionParameters, PlainCredentials, BasicProperties
from pika.exchange_type import ExchangeType
from config import RabbitSettings
from message.message import Message
from message.rabbit import RabbitMessage
from typing import Dict, List


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
        self.prefetch_count = 15
        self.is_consuming = False
        self.consumers = list()
        self.message_buffers: Dict[str, List] = dict()

        self.__connect()

    def __connect(self):
        self.logger.info('Connecting to RabbitMQ at %s:%d', self.conn_params.host, self.conn_params.port)
        self._connection = pika.SelectConnection(
            parameters=self.conn_params,
            on_open_callback=self.__on_connection_open,
            on_open_error_callback=self.__on_connection_error,
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
        self.__setup_exchange()

    def __on_channel_closed(self, channel, reason):
        self.logger.warning('Channel %i was closed. Reason: %s', channel, reason)
        self.close()

    def __setup_exchange(self):
        self.logger.info('Declaring DigSiNet exchange')
        self.mq_chan.exchange_declare(
            exchange='digsinet',
            exchange_type=ExchangeType.direct
        )

    def __on_exchange_declare_ok(self):
        self.logger.info('DigSiNet exchange declared')
        self.__setup_queues()

    def __setup_queues(self):
        self.logger.info('Declaring Queues for Siblings')
        for channel in self.channels:
            callback = functools.partial(self.__on_queue_declare_ok, chan=channel)
            self.mq_chan.queue_declare(queue=channel, auto_delete=False, callback=callback)

    def __on_queue_declare_ok(self, _unused_frame, chan):
        queue_name = chan
        self.logger.info('Binding digsinet to %s with key %s', chan, chan)
        callback = functools.partial(self.__on_bind_ok, chan=chan)
        self.mq_chan.queue_bind(
            queue_name,
            exchange='digsinet',
            routing_key=queue_name,
            callback=callback
        )

    def __on_bind_ok(self, chan):
        self.logger.info('Successfully bound %s', chan)
        self.mq_chan.basic_qos(prefetch_count=self.prefetch_count, callback=self.__on_qos_ok)

    def __on_qos_ok(self):
        self.logger.info('QoS setup successful')
        self.is_consuming = True
        self.mq_chan.add_on_cancel_callback(self.__on_channel_canceled)

    def __on_channel_canceled(self, frame):
        self.logger.warning('Channel was canceled. Reason: %r', frame)
        if self.mq_chan:
            self.mq_chan.close()

    def __on_connection_error(self, _unused_connection, error):
        self.logger.fatal('error connecting to RabbitMQ: %s', error)

    def __on_message(self, _unused_channel, basic_delivery, props: BasicProperties, body, tag):
        self.logger.info('Received message from Queue')
        self.message_buffers[tag].append(
            {'delivery_tag': basic_delivery.delivery_tag, 'body': body}
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

    def poll(self, consumer, timeout) -> Message:
        # TODO: Implement Timeout case
        start_time = time.time()
        while timeout > 0:
            if self.message_buffers[consumer]:
                msg = self.message_buffers[consumer].pop()
                return RabbitMessage(msg['body'], msg['delivery_tag'])
            else:
                time.sleep(0.1)
                elapsed_time = time.time() - start_time
                timeout -= elapsed_time
                start_time = time.time()
        return RabbitMessage('')

    def subscribe(self, channel: str, group_id: str = None):
        self.logger.info('Subscribing to %s', channel)
        tag = channel + "_" + uuid.uuid4().hex
        self.message_buffers[tag] = []
        callback = functools.partial(self.__on_message, tag)
        consumer = self.mq_chan.basic_consume(
            queue=channel,
            on_message_callback=callback,
            consumer_tag=tag
        )
        self.message_buffers[consumer] = list()
        self.consumers.append(consumer)
        return consumer

    def get_sibling_channels(self):
        return self.channels

    def new_sibling_channel(self, channel: str):
        if channel not in self.channels:
            self.logger.info(f"Creating new channel {channel}...")
            callback = functools.partial(self.__on_queue_declare_ok, chan=channel)
            self.mq_chan.queue_declare(queue=channel, callback=callback)

    def close(self):
        self.is_consuming = False
        if self._connection.is_closing or self._connection.is_closed:
            self.logger.info('Connection already closed')
        else:
            self._connection.close()
