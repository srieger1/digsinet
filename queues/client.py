# TODO: rename to rabbitmq_client.py
import pika
import json
from pika.exchange_type import ExchangeType

class MessageQueueClient:
    '''
    Client for publishing and consuming topology updates via a RabbitMQ server.
    '''
    def __init__(self, host: str , username: str, password: str, queues: list[str]):
        '''
        Create a Client to connecto to a RabbitMQ server to receive and publish topology updates.

        Establishes a connection to the server at `host`, using `username` and `password`.
        Initializes an exchange called `digsinet` and a queue for each entry in `queues` bound to the exchange.
        Routing keys are the queue names. Throws exception if connection to the RabbitMQ server can not be established
        '''
        self.host = host
        self.queues = queues
        self.credentials = pika.PlainCredentials(username, password)
        connection_params = pika.ConnectionParameters(
            self.host,
            5672,
            '/',
            self.credentials
        )
        self.conn = pika.BlockingConnection(connection_params)
        self.channel = self.conn.channel()
        self.channel.confirm_delivery()

        self.channel.exchange_declare(
            exchange='digsinet',
            exchange_type=ExchangeType.direct,
            passive=False,
            durable=True,
            auto_delete=False
        )

        for queue in queues:
            self.channel.queue_declare(
                queue=queue,
                auto_delete=False
            )
            self.channel.queue_bind(
                queue=queue,
                exchange='digsinet',
                routing_key=queue
            )


    def has_messages(self, queue: str) -> bool:
        '''
        Check if new Messages are available in the Queue.

        Redeclares the queue given, utilizing the fact that redeclaring an existing Queue
        will return information about it, including the current message count.
        '''
        res = self.channel.queue_declare(
            queue=queue,
            durable=True,
            exclusive=False,
            auto_delete=False,
            passive=True
        )
        return res.method.message_count != 0


    def qsize(self, queue: str) -> int:
        '''
        Return the count of messages currently in the queue.        
        '''
        res = self.channel.queue_declare(
            queue=queue,
            durable=True,
            exclusive=False,
            auto_delete=False,
            passive=True
        )
        return res.method.message_count


    def get(self, queue: str):
        method_frame, header_frame, body = self.channel.basic_get(queue)
        if method_frame:
            self.channel.basic_ack(method_frame.delivery_tag)
            return json.loads(body)
        else:
            return None

    
    def put(self, queue: str, value):
        self.channel.basic_publish(exchange='digsinet', routing_key=queue, body=json.dumps(value, default= lambda obj: '<not serializable>'), mandatory=True)


    def queue_names(self) -> list[str]:
        return self.queues


    


