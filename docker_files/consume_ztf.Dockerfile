FROM python:3.7

ADD consume.py /

RUN pip install pgbroker

CMD [ "python", "./consume_ztf.py.py" ]
