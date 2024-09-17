import json
from confluent_kafka import Consumer, KafkaError
from datetime import datetime, timedelta

model = {}

def update_model(notification):
    timestamp = None
    prefix = ""
    for key, value in notification.items():
        if key == "update":
            if "timestamp" in value.keys():
                timestamp = value["timestamp"]
            if "prefix" in value.keys():
                prefix = value["prefix"]
            if "update" in value.keys():
                for update in value["update"]:
                    path = prefix + update['path']
                    value = None
                    if "val" in update.keys():
                        value = update['val']
                    model[path] = {
                        "timestamp": timestamp,
                        "value": value
                    }
        #elif key == "delete":
        elif key == "sync_response":
            print("Sync response ignored")
        else:
            print(f"Unknown key: {key}")

def main():
    # Kafka consumer configuration
    conf = {
        'bootstrap.servers': 'localhost:29092',  # Adjust this to your Kafka broker address
        'group.id': 'realnet_aggregator',
        'auto.offset.reset': 'earliest'
    }

    # Create Consumer instance
    consumer = Consumer(conf)

    # Subscribe to the 'realnet' topic
    consumer.subscribe(['realnet'])

    # Calculate the timestamp for 10 minutes ago
    start_time = int((datetime.now() - timedelta(minutes=10)).timestamp() * 1000)

    # Dictionary to store the aggregated data
    aggregated_data = {}

    try:
        while True:
            msg = consumer.poll(1.0)

            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    print(f"Reached end of partition {msg.topic()}/{msg.partition()}")
                else:
                    print(f"Error: {msg.error()}")
            else:
                # Check if the message timestamp is after our start time
                if msg.timestamp()[1] >= start_time:
                    try:
                        # Decode the message value as JSON
                        notification = json.loads(msg.value().decode('utf-8'))
                        
                        # update model
                        update_model(notification)
                        
                        print(f"Processed message from {msg.topic()}:{msg.partition()}:{msg.offset()}")
                    except json.JSONDecodeError:
                        print(f"Failed to decode message as JSON: {msg.value()}")
                else:
                    print(f"Skipping message with timestamp {msg.timestamp()[1]} (before start time)")

    except KeyboardInterrupt:
        pass
    finally:
        # Print the final aggregated data
        print("Final aggregated model:")
        print(json.dumps(model, indent=2))
        
        # Close down consumer to commit final offsets.
        consumer.close()

if __name__ == "__main__":
    main()