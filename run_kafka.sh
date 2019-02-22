#!/usr/bin/env bash

read -p "Enter kafka directory: " path

# Check if directory exists
if [ ! -e "$path" ]
then
  echo "Given directory does not exist"
fi

$path/bin/zookeeper-server-start.sh  $path/config/zookeeper.properties &
$path/bin/kafka-server-start.sh  $path/config/server.properties &
$path/bin/kafka-console-producer.sh --broker-list localhost:9092 --topic Demo-Topic &&
kill $!
