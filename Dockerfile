FROM python:3.10-slim-bullseye

WORKDIR /app

COPY . /app/

RUN \
  apt update && \
  apt install -y --no-install-recommends gcc libcairo2-dev libgeos-dev && \
  pip install --upgrade pip && \
  pip install . && \
  mkdir -p /maps/cache

VOLUME ["/maps"]
ENTRYPOINT ["map-machine"]

