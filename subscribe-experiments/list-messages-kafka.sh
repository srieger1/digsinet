#!/bin/bash

echo "Content of topic realnet:"
docker exec -it kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic realnet --from-beginning

echo "Content of topic continuous_integration:"
docker exec -it kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic continuous_integration --from-beginning

echo "Content of topic security:"
docker exec -it kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic security --from-beginning

echo "Content of topic traffic_engineering:"
docker exec -it kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic traffic_engineering --from-beginning
