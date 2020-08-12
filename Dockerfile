FROM python:3

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
  && apt-get install --no-install-recommends -y \
     python3-openslide \
  && rm -rf /var/lib/apt/lists/*

ADD requirements.txt /requirements.txt
RUN pip3 install -r requirements.txt

ADD . /wsi_service
RUN pip install -e /wsi_service

VOLUME ["/data"]
EXPOSE 8080/tcp
ENTRYPOINT ["python", "-m", "wsi_service", "--port", "8080", "/data"]