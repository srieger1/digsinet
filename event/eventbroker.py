from abc import ABC, abstractmethod
from typing import List
from logging import Logger


class EventBroker(ABC):
    def __init__(self, config, channels: List[str], logger: Logger):
        pass

    @abstractmethod
    def publish(self, channel: str, data):
        pass

    @abstractmethod
    def poll(self, channel: str, timeout):
        pass

    @abstractmethod
    def subscribe(self, channel: str):
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
