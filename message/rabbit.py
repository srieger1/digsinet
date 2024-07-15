from message.message import Message


class RabbitMessage(Message):
    def __init__(self, message):
        super().__init__(message)
        self.message = message

    def error(self):
        pass

    def value(self):
        return self.message
