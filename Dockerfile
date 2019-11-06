# Linux starting point

FROM golang:1.13-alpine

RUN apk add --no-cache bash python3
RUN pip3 install --no-cache-dir requests

SHELL ["/bin/bash", "-c"]
LABEL com.frauscher.vendor="Frauscher Sensortechnik GmbH ©2019"

WORKDIR /opt
COPY *.py /opt/Frauscher/bin/
COPY known_licenses.json /opt/Frauscher/etc/known_licenses.json

ENV PATH /opt/Frauscher/bin:$PATH

WORKDIR /work
CMD license_scanner.py --report
