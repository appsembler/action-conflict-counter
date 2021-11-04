FROM python:3.9-slim

RUN apt-get update \
    && apt-get install --no-install-recommends -y git \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY conflicts-counter.py /conflicts-counter.py

ENTRYPOINT ["/conflicts-counter.py"]
