# Slim used to reduce image size
FROM python:3.7-slim

# Configure Environment variables
ENV PYTHONPATH "Pitt-Google-Broker/:${PYTHONPATH}"
ENV GOOGLE_CLOUD_PROJECT "ardent-cycling-243415"
ENV ztf_server "public2.alerts.ztf.uw.edu:9094"
ENV ztf_principle "pitt-reader@KAFKA.SECURE"
ENV ztf_keytab_path "pitt-reader.user.keytab"
ENV PATH="/root/miniconda3/bin:${PATH}"
ARG PATH="/root/miniconda3/bin:${PATH}"

# Copy credentials and runtime files
COPY docker_files/consume_ztf.py docker_files/consume_ztf.py
COPY krb5.conf /etc/krb5.conf
COPY pitt-reader.user.keytab pitt-reader.user.keytab

# Install utils for fetching remote source code
RUN apt-get update && \
    apt-get install -y git wget python-dev gcc krb5-user python3-kafka python3-confluent-kafka libsasl2-dev libsasl2-modules-gssapi-mit libsasl2-2 libsasl2-modules && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

RUN wget \
    https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh \
    && mkdir /root/.conda \
    && bash Miniconda3-latest-Linux-x86_64.sh -b \
    && rm -f Miniconda3-latest-Linux-x86_64.sh

RUN conda install -c stuarteberg -c conda-forge librdkafka -y

# Get broker source code and install dependencies
RUN git clone --single-branch --branch master --depth 1 https://github.com/mwvgroup/Pitt-Google-Broker && \
    rm -rf Pitt-Google-Broker/.git

RUN pip install -r Pitt-Google-Broker/requirements.txt

# Launch the ZTF consumer
CMD [ "python", "docker_files/consume_ztf.py" ]
