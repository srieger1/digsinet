from message.message import Message


class KafkaMessage(Message):
    def __init__(self, message):
        self.kafka_message = message

    def error(self):
        # FIX (version-mismatch-bugs): the original condition was inverted. It returned
        # None whenever a real message was present, so genuine Kafka error/EOF events were
        # never surfaced to callers; and when kafka_message was falsy it called .error() on
        # None, raising AttributeError. This was the root cause of the downstream
        # JSONDecodeError in controller.py (None payloads slipped through unfiltered).
        # Original:
        # if self.kafka_message:
        #     return None
        # return self.kafka_message.error()
        if self.kafka_message:
            return self.kafka_message.error()
        return None

    def value(self):
        # FIX (version-mismatch-bugs): value() decoded unconditionally, so an error/EOF
        # event (where value() is None) raised AttributeError on None.decode(). Guard it
        # and return None so callers can skip non-data messages instead of crashing.
        # Original:
        # return self.kafka_message.value().decode("utf-8")
        if self.kafka_message:
            return self.kafka_message.value().decode("utf-8")
        return None
