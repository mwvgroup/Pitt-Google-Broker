FROM python:3.7

MAINTAINER Daniel Perrefort "djperrefort@pitt.edu"

# Install git
RUN apt-get update
RUN apt-get install -y git

RUN git clone https://github.com/mwvgroup/Pitt-Google-Broker
RUN git checkout djperrefort/docker

ADD consume.py /

CMD [ "python", "./Pitt-Google-Broker/scripts/consume_ztf.py" ]
