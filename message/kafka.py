from message.message import Message

class KafkaMessage(Message):
    def __init__(self, message):
        self.kafka_message = message

    def error(self):
        return self.kafka_message.error()

    def value(self):
        return self.kafka_message.value().decode('utf-8')
