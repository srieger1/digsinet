from abc import ABC, abstractmethod
from typing import List
from logging import Logger
from message.message import Message


class EventBroker(ABC):
    def __init__(self, config, channels: List[str], logger: Logger):
        pass

    @abstractmethod
    def publish(self, channel: str, data):
        pass

    @abstractmethod
    def poll(self, consumer, timeout) -> Message:
        pass

    @abstractmethod
    def subscribe(self, channel: str, group_id: str = None):
        pass

    @abstractmethod
    def get_sibling_channels(self):
        pass

    @abstractmethod
    def new_sibling_channel(self, channel: str):
        pass

    @abstractmethod
    def close(self):
        pass

    @abstractmethod
    def close_consumer(self):
        pass
