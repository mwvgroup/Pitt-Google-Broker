# Based on Ubuntu
FROM python:3.7

# Install utils for fetching remote source code
RUN apt-get update
RUN apt-get install -y git curl


# Install miniconda to /miniconda
# RUN curl -LO http://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh
# RUN bash Miniconda3-latest-Linux-x86_64.sh -p /miniconda -b
# RUN rm Miniconda3-latest-Linux-x86_64.sh
# ENV PATH=/miniconda/bin:${PATH}

# Install the Apache Kafka protocol
# RUN conda config --set remote_read_timeout_secs 240
# RUN conda config --set ssl_verify false
# RUN conda install -c conda-forge librdkafka
RUN apt-get install librdkafka-dev python-dev -y

# Get broker source code and install dependencies
# Some installs may fail without numpy, so we install it first
RUN git clone https://github.com/mwvgroup/Pitt-Google-Broker
RUN pip install numpy
RUN pip install -r Pitt-Google-Broker/requirements.txt

# Copy credentials files
COPY GCPauth.json GCPauth.json
COPY krb5.conf krb5.conf
COPY pitt-reader.user.keytab pitt-reader.user.keytab

# Configure Environment variables
ENV PYTHONPATH "Pitt-Google-Broker/:${PYTHONPATH}"
ENV GOOGLE_CLOUD_PROJECT "ardent-cycling-243415"
ENV GOOGLE_APPLICATION_CREDENTIALS "GCPauth.json"
ENV ztf_server "public2.alerts.ztf.uw.edu:9094"
ENV ztf_principle "pitt-reader@KAFKA.SECURE"
ENV ztf_keytab_path "pitt-reader.user.keytab"

# Launch the ZTF consumer
COPY consume_ztf.py consume_ztf.py
CMD [ "python", "consume_ztf.py" ]
