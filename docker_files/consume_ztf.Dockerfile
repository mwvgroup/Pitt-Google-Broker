# Slim used to reduce image size
FROM python:3.7-slim

# Configure Environment variables
ENV PYTHONPATH "Pitt-Google-Broker/:${PYTHONPATH}"
ENV GOOGLE_CLOUD_PROJECT "ardent-cycling-243415"
ENV ztf_server "public2.alerts.ztf.uw.edu:9094"
ENV ztf_principle "pitt-reader@KAFKA.SECURE"
ENV ztf_keytab_path "pitt-reader.user.keytab"

# Copy credentials and runtime files
COPY docker_files/consume_ztf.py docker_files/consume_ztf.py
COPY krb5.conf krb5.conf
COPY pitt-reader.user.keytab pitt-reader.user.keytab

# Install utils for fetching remote source code
RUN apt-get update && \
    apt-get install -y git librdkafka-dev python-dev gcc && \
    apt-get clean

# Get broker source code and install dependencies
RUN git clone --single-branch --branch master --depth 1 https://github.com/mwvgroup/Pitt-Google-Broker && \
    rm -rf Pitt-Google-Broker/.git

RUN pip install -r Pitt-Google-Broker/requirements.txt && \
    pip cache purge

# Launch the ZTF consumer
CMD [ "python", "docker_files/consume_ztf.py" ]
