FROM golang:1.13-alpine AS build
RUN apk add --no-cache bash python3
COPY . /src
WORKDIR /src
RUN python3 -m pip install setuptools wheel
RUN python3 setup.py bdist_wheel

FROM golang:1.13-alpine

RUN apk add --no-cache bash python3
SHELL ["/bin/bash", "-c"]
LABEL com.frauscher.vendor="Frauscher Sensortechnik GmbH ©2019"

WORKDIR /opt
COPY --from=build /src/dist/*.whl /opt/Frauscher/pkg/
RUN python3 -m pip install /opt/Frauscher/pkg/*.whl
COPY run_scanner.py /opt/Frauscher/bin/

ENV PATH /opt/Frauscher/bin:$PATH

WORKDIR /work
ENTRYPOINT ["run_scanner.py", \
            "--cache=resources/license-cache.json", \
            "--json=resources/licenses.json"]
