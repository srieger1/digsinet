# TODO: Make a new channel for each subscribe

import threading
import pika
import json
import functools
import uuid
import time

from event.eventbroker import EventBroker
from logging import Logger
from pika import ConnectionParameters, PlainCredentials
from pika.exchange_type import ExchangeType
from pika.channel import Channel
from pika.adapters.asyncio_connection import AsyncioConnection
from config import RabbitSettings
from message.message import Message
from message.rabbit import RabbitMessage
from typing import List, Dict


class Consumer:
    def __init__(self, queue: str, tag: str, channel: Channel):
        self.queue = queue
        self.channel = channel
        self.message_buffer = []

        callback = functools.partial(self.__on_message, tag)

        self.channel.basic_consume(
            queue=self.queue,
            auto_ack=False,
            exclusive=True,
            consumer_tag=tag,
            on_message_callback=callback
        )

    def __on_message(self, tag, _channel, delivery, _props, body):
        self.message_buffer.append({'delivery_tag': delivery.delivery_tag, 'data': body})

    def has_messages(self):
        if len(self.message_buffer) > 0:
            return True
        else:
            return False

    def get_message(self):
        message = self.message_buffer.pop(0)
        self.channel.basic_ack(delivery_tag=message['delivery_tag'])
        return message['data']

    def close(self):
        self.channel.close()


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
                                                credentials=PlainCredentials(config.username, config.password,
                                                                             True))

        self._connection = None
        self.admin_channel = None
        self.prefetch_count = 15
        self.consumers: Dict[str, Consumer] = {}

        self.is_ready = False
        self._io_thread = None

        self.__connect()

    def __connect(self):
        self.logger.info('Connecting to RabbitMQ at %s:%d', self.conn_params.host, self.conn_params.port)
        self._connection = AsyncioConnection(
            parameters=self.conn_params,
            on_open_callback=self.__on_connection_open,
            on_open_error_callback=self.__on_connection_error,
        )
        self._io_thread = threading.Thread(target=self._connection.ioloop.run_forever)
        self._io_thread.start()

    def __on_connection_open(self, _unused_connection):
        self.logger.info('Connection to RabbitMQ has been opened')
        self.__open_channel()

    def __open_channel(self):
        self.logger.info('Creating new RabbitMQ channel')
        self._connection.channel(on_open_callback=self.__on_open_channel)

    def __on_open_channel(self, channel):
        self.logger.info('Channel opened')
        self.admin_channel = channel
        self.admin_channel.add_on_close_callback(self.__on_channel_closed)
        self.__setup_exchange()

    def __on_channel_closed(self, channel, reason):
        self.logger.warning('Channel %i was closed. Reason: %s', channel, reason)
        self.close()

    def __setup_exchange(self):
        self.logger.info('Declaring DigSiNet exchange')
        self.admin_channel.exchange_declare(
            exchange='digsinet',
            exchange_type=ExchangeType.direct,
            callback=self.__on_exchange_declare_ok
        )

    def __on_exchange_declare_ok(self, exchange_name):
        self.logger.info(f'Exchange {exchange_name} declared successfully')
        self.__setup_queues()

    def __setup_queues(self):
        self.logger.info('Declaring Queues for Siblings')
        for channel in self.channels:
            callback = functools.partial(self.__on_queue_declare_ok, chan=channel)
            self.admin_channel.queue_declare(queue=channel, auto_delete=False, callback=callback)

    def __on_queue_declare_ok(self, _unused_frame, chan):
        queue_name = chan
        self.logger.info('Binding digsinet to %s with key %s', chan, chan)
        callback = functools.partial(self.__on_bind_ok, chan=chan)
        self.admin_channel.queue_bind(
            queue_name,
            exchange='digsinet',
            routing_key=queue_name,
            callback=callback
        )

    def __on_bind_ok(self, _unused_frame, chan):
        self.logger.info('Successfully bound %s', chan)
        self.admin_channel.basic_qos(prefetch_count=self.prefetch_count, callback=self.__on_qos_ok)

    def __on_qos_ok(self, _unused_frame):
        self.logger.info('QoS setup successful')
        self.is_ready = True
        self.admin_channel.add_on_cancel_callback(self.__on_channel_canceled)

    def __on_channel_canceled(self, frame):
        self.logger.warning('Channel was canceled. Reason: %r', frame)
        if self.admin_channel:
            self.admin_channel.close()

    def __on_connection_error(self, _unused_connection, error):
        self.logger.fatal('error connecting to RabbitMQ: %s', error)

    def __make_consumer(self, queue: str, tag: str, event: threading.Event):
        self.logger.info(f'Creating consumer for tag {tag}...')
        callback = functools.partial(self.__on_consumer_open, tag=tag, event=event, queue=queue)
        self._connection.channel(on_open_callback=callback)

    def __on_consumer_open(self, channel: Channel, queue: str, tag: str, event: threading.Event):
        self.logger.info(f'Channel for consumer {tag} opened')
        callback = functools.partial(self.__on_consumer_qos, channel=channel, event=event, tag=tag, queue=queue)
        channel.basic_qos(prefetch_count=self.prefetch_count, callback=callback)

    def __on_consumer_qos(self, _unused_frame, channel: Channel, queue: str, tag: str, event: threading.Event):
        self.logger.info(f'QoS for consumer {tag} setup successful')
        consumer = Consumer(queue, tag, channel)
        self.consumers[tag] = consumer
        event.set()

    def publish(self, channel: str, data):
        # TODO: Get rid of the nasty '<not serializable>' later down the line
        self.logger.info(f"Publishing message to topic {channel}: {json.dumps(data, default=lambda obj: '<not serializable>')}")
        self.admin_channel.basic_publish(
            exchange='digsinet',
            routing_key=channel,
            body=json.dumps(data, default=lambda obj: '<not serializable>'),
            mandatory=True
        )

    def poll(self, consumer, timeout) -> Message:
        if consumer in self.consumers:
            consumer = self.consumers[consumer]
            start_time = time.time()
            while timeout > 0:
                if consumer.has_messages():
                    msg = consumer.get_message()
                    return RabbitMessage(msg['body'])
                time.sleep(0.1)
                elapsed_time = time.time() - start_time
                timeout -= elapsed_time
                start_time = time.time()
        return RabbitMessage('')

    def subscribe(self, channel: str, group_id: str = None):
        if not self.is_ready:
            while not self.is_ready:
                time.sleep(0.1)
        tag = channel + "_" + uuid.uuid4().hex
        self.logger.info('Subscribing to %s with tag %s', channel, tag)
        event = threading.Event()
        self.__make_consumer(channel, tag, event)

        event.wait()

        return tag, tag

    def get_sibling_channels(self):
        return self.channels

    def new_sibling_channel(self, channel: str):
        if channel not in self.channels:
            self.logger.info(f"Creating new channel {channel}...")
            self.channels.append(channel)
            callback = functools.partial(self.__on_queue_declare_ok, chan=channel)
            self.admin_channel.queue_declare(queue=channel, callback=callback)

    def close(self):
        self.is_ready = False
        if self._connection.is_closing or self._connection.is_closed:
            self.logger.info('Connection already closed')
        else:
            self._connection.close()

    def close_consumer(self):
        pass