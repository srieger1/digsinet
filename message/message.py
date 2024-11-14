from abc import ABC, abstractmethod


class Message(ABC):
    def __init__(self, message):
        pass

    @abstractmethod
    def error(self):
        pass

    @abstractmethod
    def value(self):
        pass
