FROM python:3.10

WORKDIR /app

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY querier querier
COPY server server
COPY common common
COPY test test
COPY secret.py secret.py
