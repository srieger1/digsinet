#!/bin/bash

docker exec -it kafka kafka-topics --bootstrap-server localhost:9092 --list

docker exec -it kafka kafka-topics --bootstrap-server localhost:9092 --delete --topic realnet
docker exec -it kafka kafka-topics --bootstrap-server localhost:9092 --delete --topic security
docker exec -it kafka kafka-topics --bootstrap-server localhost:9092 --delete --topic continuous_integration
docker exec -it kafka kafka-topics --bootstrap-server localhost:9092 --delete --topic traffic_engineering 

#docker exec -it kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic realnet --form-beginning
