from message.message import Message

class RabbitMessage(Message):
    def __init__(self, message, delivery_tag=None):
        super.__init__(message)
        self.delivery_tag = delivery_tag
        self.message = message

    def error(self):
        pass

    def value(self):
        return self.message
