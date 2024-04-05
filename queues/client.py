import pika
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
        self.conn = pika.BlockingConnection(host, credentials=self.credentials)
        self.channel = self.conn.channel()

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
    

