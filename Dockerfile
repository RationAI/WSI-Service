FROM registry.gitlab.com/empaia/integration/ci-docker-images/test-runner:0.1.44@sha256:f0e64d6d6490f152ac8b2eb2d5b4c44b7fc55c5bd30b6de8b77058cdf27da2d8 AS wsi_service_build

# EDIT to set version of OpenSlide
ENV OPENSLIDE_VERSION=3390d5a

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
  && apt-get install --no-install-recommends -y \
  python3-openslide

RUN mkdir /openslide_deps

RUN curl -o /usr/lib/x86_64-linux-gnu/libopenslide.so.0 \
  https://gitlab.com/api/v4/projects/36668960/packages/generic/libopenslide.so.0/$OPENSLIDE_VERSION/libopenslide.so.0

RUN cp /usr/lib/x86_64-linux-gnu/libopenslide.so.0 /openslide_deps
RUN ldd /usr/lib/x86_64-linux-gnu/libopenslide.so.0 \
  | grep "=> /" | awk '{print $3}' | xargs -I '{}' cp -v '{}' /openslide_deps

RUN curl -o /tmp/libpixman-1-0_0.40.0-1build3_amd64.deb \
  http://launchpadlibrarian.net/562429593/libpixman-1-0_0.40.0-1build3_amd64.deb
RUN dpkg -i /tmp/libpixman-1-0_0.40.0-1build3_amd64.deb
ENV LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libpixman-1.so.0.40.0

COPY . /wsi-service

WORKDIR /wsi-service
RUN poetry build && poetry export -f requirements.txt > requirements.txt

WORKDIR /wsi-service/wsi_service_base_plugins/tifffile
RUN poetry build && poetry export -f requirements.txt > requirements.txt

WORKDIR /wsi-service/wsi_service_base_plugins/openslide
RUN poetry build && poetry export -f requirements.txt > requirements.txt

WORKDIR /wsi-service/wsi_service_base_plugins/pil
RUN poetry build && poetry export -f requirements.txt > requirements.txt

WORKDIR /wsi-service/wsi_service_base_plugins/wsidicom
RUN poetry build && poetry export -f requirements.txt > requirements.txt


FROM wsi_service_build AS wsi_service_dev

WORKDIR /wsi-service
RUN poetry install


FROM registry.gitlab.com/empaia/integration/ci-docker-images/test-runner:0.1.44@sha256:f0e64d6d6490f152ac8b2eb2d5b4c44b7fc55c5bd30b6de8b77058cdf27da2d8 AS wsi_service_intermediate

RUN mkdir /artifacts
COPY --from=wsi_service_build /wsi-service/requirements.txt /artifacts
RUN pip install -r /artifacts/requirements.txt
COPY --from=wsi_service_build /wsi-service/wsi_service_base_plugins/tifffile/requirements.txt /artifacts/requirements_tiffile.txt
RUN pip install -r /artifacts/requirements_tiffile.txt
COPY --from=wsi_service_build /wsi-service/wsi_service_base_plugins/openslide/requirements.txt /artifacts/requirements_openslide.txt
RUN pip install -r /artifacts/requirements_openslide.txt
COPY --from=wsi_service_build /wsi-service/wsi_service_base_plugins/pil/requirements.txt /artifacts/requirements_pil.txt
RUN pip install -r /artifacts/requirements_pil.txt
COPY --from=wsi_service_build /wsi-service/wsi_service_base_plugins/wsidicom/requirements.txt /artifacts/requirements_wsidicom.txt
RUN pip install -r /artifacts/requirements_wsidicom.txt

COPY --from=wsi_service_build /wsi-service/dist/ /wsi-service/dist/
COPY --from=wsi_service_build /wsi-service/wsi_service_base_plugins/openslide/dist/ /wsi-service/dist/
COPY --from=wsi_service_build /wsi-service/wsi_service_base_plugins/pil/dist/ /wsi-service/dist/
COPY --from=wsi_service_build /wsi-service/wsi_service_base_plugins/tifffile/dist/ /wsi-service/dist/
COPY --from=wsi_service_build /wsi-service/wsi_service_base_plugins/wsidicom/dist/ /wsi-service/dist/

RUN pip3 install /wsi-service/dist/*.whl

RUN mkdir /data


FROM ubuntu:20.04@sha256:35ab2bf57814e9ff49e365efd5a5935b6915eede5c7f8581e9e1b85e0eecbe16 AS wsi_service_production

RUN apt-get update \
  && apt-get install --no-install-recommends -y python3 python3-pip \
  && rm -rf /var/lib/apt/lists/*

RUN adduser --disabled-password --gecos '' appuser \
  && mkdir /artifacts && chown appuser:appuser /artifacts \
  && mkdir -p /opt/app/bin && chown appuser:appuser /opt/app/bin
USER appuser

COPY --chown=appuser --from=wsi_service_build /openslide_deps/* /usr/lib/x86_64-linux-gnu/
COPY --chown=appuser --from=wsi_service_build /usr/lib/x86_64-linux-gnu/libpixman-1.so.0.40.0 /usr/lib/x86_64-linux-gnu/libpixman-1.so.0.40.0
ENV LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libpixman-1.so.0.40.0

COPY --chown=appuser --from=wsi_service_intermediate /usr/local/lib/python3.8/dist-packages/ /usr/local/lib/python3.8/dist-packages/
COPY --chown=appuser --from=wsi_service_intermediate /data /data

ENV WEB_CONCURRENCY=8

EXPOSE 8080/tcp

WORKDIR /usr/local/lib/python3.8/dist-packages/wsi_service

CMD ["python3", "-m", "uvicorn", "wsi_service.api:api", "--host", "0.0.0.0", "--port", "8080", "--loop=uvloop", "--http=httptools"]
