FROM python:3.7

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

# Copy credentials files
COPY GCPauth.json GCPauth.json
COPY krb5.conf krb5.conf
COPY pitt-reader.user.keytab pitt-reader.user.keytab

# Configure Environment variables
ENV PYTHONPATH="Pitt-Google-Broker/:${PYTHONPATH}"
ENV GOOGLE_CLOUD_PROJECT="ardent-cycling-243415"
ENV GOOGLE_APPLICATION_CREDENTIALS="GCPauth.json"
ENV ztf_server="public2.alerts.ztf.uw.edu:9094"
ENV ztf_principle="pitt-reader@KAFKA.SECURE"
ENV ztf_keytab_path="pitt-reader.user.keytab"


CMD [ "python", "consume_ztf.py" ]
