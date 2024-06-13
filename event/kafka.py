from typing import List
from event.__init__ import EventBroker


class KafkaClient(EventBroker):
    def __init__(self, config, channels: List[str], logger):
        pass

    def publish(self, channel: str, data):
        pass

    def poll(self, channel: str, timeout):
        pass

    def subscribe(self, channel: str):
        pass

    def get_sibling_channels(self):
        pass

    def new_sibling_channel(self, channel: str):
        pass

    def close(self):
        pass
