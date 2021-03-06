FROM ubuntu:20.04

ENV TZ=Europe/Berlin
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update && \
    apt-get install -y texlive-full && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /data
VOLUME ["/data"]
