FROM python:3.7

MAINTAINER Daniel Perrefort "djperrefort@pitt.edu"

COPY consume_ztf.py consume_ztf.py

# Install git
RUN apt-get update
RUN apt-get install -y git

# Get broker source code and add to path
RUN git clone https://github.com/mwvgroup/Pitt-Google-Broker

# Install dependencies
# Some dependency installs may fail without numpy, so we install it first
RUN pip install numpy
RUN pip install -r Pitt-Google-Broker/requirements.txt

# Configure Python Environment
ENV PYTHONPATH="Pitt-Google-Broker/:${PYTHONPATH}"


CMD [ "python", "./consume_ztf.py" ]
