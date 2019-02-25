FROM ubuntu
COPY . /usr/src/pitt_broker/
WORKDIR /usr/src/pitt_broker/

RUN apt-get update && apt-get upgrade -y
RUN apt-get install -y wget

# Install languages
RUN apt install -y python3.7
RUN apt install -y default-jre

# Python packages
RUN apt-get install -y python3-pip
RUN pip3 install -r ./requirements.txt

# Stuff needed to run Apache Kafka
# This still requires some thinking over....
RUN apt-get install -y zookeeperd
RUN wget http://www-eu.apache.org/dist/kafka/1.0.0/kafka_2.12-1.0.0.tgz
RUN mkdir /usr/src/Kafka
RUN tar xvzf kafka_2.12-1.0.0.tgz -C /usr/src/Kafka
RUN rm kafka_2.12-1.0.0.tgz
