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
