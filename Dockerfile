FROM python:3.5-stretch AS build

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
  && apt-get install --no-install-recommends -y \
     python3-openslide

ADD requirements.txt /requirements.txt
RUN pip3 install -r requirements.txt

ADD . /wsi_service
RUN pip3 install -e /wsi_service

RUN mkdir /openslide_deps
RUN cp /usr/lib/x86_64-linux-gnu/libopenslide.so.0 /openslide_deps
RUN ldd /usr/lib/x86_64-linux-gnu/libopenslide.so.0 \
  | grep "=> /" | awk '{print $3}' | xargs -I '{}' cp -v '{}' /openslide_deps

RUN mkdir /data


FROM gcr.io/distroless/python3:nonroot


COPY --from=build --chown=nonroot:nonroot /usr/local/lib/python3.5/site-packages/ /usr/lib/python3.5/.
COPY --from=build --chown=nonroot:nonroot /openslide_deps/* /usr/lib/x86_64-linux-gnu/

COPY --from=build --chown=nonroot:nonroot /wsi_service /wsi_service
RUN python -m pip install -e /wsi_service

COPY --from=build --chown=nonroot:nonroot /data /data
VOLUME ["/data"]

EXPOSE 8080/tcp

ENTRYPOINT ["python", "-m", "wsi_service", "--port", "8080", "/data"]