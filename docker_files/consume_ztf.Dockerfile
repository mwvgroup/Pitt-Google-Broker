FROM python:3.7

MAINTAINER Daniel Perrefort "djperrefort@pitt.edu"

# Install git
RUN apt-get update
RUN apt-get install -y git

RUN git clone https://github.com/mwvgroup/Pitt-Google-Broker

# This can be removed after merging djperrefort/docker into master
RUN cd ./Pitt-Google-Broker/; git checkout djperrefort/docker; cd ../

# Install dependencies
# Some dependency installs may fail without numpy, so we install it first
RUN pip install numpy
RUN pip install -r Pitt-Google-Broker/requirements.txt

# Configure Python Environment
ENV PYTHONPATH="Pitt-Google-Broker/:${PYTHONPATH}"

CMD [ "python", "./Pitt-Google-Broker/scripts/consume_ztf.py" ]
