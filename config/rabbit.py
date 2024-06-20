from pydantic import BaseModel


class RabbitSettings(BaseModel):
    """
    Settings for RabbitMQ.

    Attributes:
        host (str): Hostname of the RabbitMQ server.
        port (int): Port where RabbitMQ listens. Defaults to 5672.
        username (str): RabbitMQ username.
        password (str): RabbitMQ password.
    """
    host: str
    port: int = 5672
    username: str
    password: str

