FROM python:3.7

MAINTAINER Daniel Perrefort "djperrefort@pitt.edu"

# Install git
RUN apt-get update
RUN apt-get install -y git

RUN git clone --single-branch --branch djperrefort/docker https://github.com/mwvgroup/Pitt-Google-Broker

CMD [ "python", "./Pitt-Google-Broker/scripts/consume_ztf.py" ]
