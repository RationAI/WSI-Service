FROM registry.gitlab.com/empaia/integration/ci-docker-images/test-runner:0.2.8@sha256:0c20dd487c2bb040fd78991bf54f396cb1fd9ab314a7a55bee0ad4909748797d AS wsi_service_build

ENV DEBIAN_FRONTEND=noninteractive

COPY . /wsi-service

WORKDIR /wsi-service
RUN poetry build && poetry export -f requirements.txt > requirements.txt

WORKDIR /wsi-service/wsi_service_base_plugins/openslide
RUN poetry build && poetry export -f requirements.txt > requirements.txt

WORKDIR /wsi-service/wsi_service_base_plugins/pil
RUN poetry build && poetry export -f requirements.txt > requirements.txt

WORKDIR /wsi-service/wsi_service_base_plugins/tifffile
RUN poetry build && poetry export -f requirements.txt > requirements.txt

WORKDIR /wsi-service/wsi_service_base_plugins/tiffslide
RUN poetry build && poetry export -f requirements.txt > requirements.txt

WORKDIR /wsi-service/wsi_service_base_plugins/wsidicom
RUN poetry build && poetry export -f requirements.txt > requirements.txt

# TODO: what about this plugin - needed? not in main Dockerfile
WORKDIR /wsi-service/wsi_service_base_plugins/tifffile_generic
RUN poetry build && poetry export -f requirements.txt > requirements.txt


FROM wsi_service_build AS wsi_service_dev

WORKDIR /wsi-service
RUN poetry install


FROM ubuntu:22.04@sha256:bcc511d82482900604524a8e8d64bf4c53b2461868dac55f4d04d660e61983cb AS wsi_service_intermediate

RUN apt-get update \
  && apt-get install --no-install-recommends -y build-essential python3-pip python3-packaging python3-dev \
  && rm -rf /var/lib/apt/lists/*

RUN mkdir /artifacts
COPY --from=wsi_service_build /wsi-service/requirements.txt /artifacts
RUN pip install -r /artifacts/requirements.txt

COPY --from=wsi_service_build /wsi-service/wsi_service_base_plugins/openslide/requirements.txt /artifacts/requirements_openslide.txt
RUN pip install -r /artifacts/requirements_openslide.txt
COPY --from=wsi_service_build /wsi-service/wsi_service_base_plugins/pil/requirements.txt /artifacts/requirements_pil.txt
RUN pip install -r /artifacts/requirements_pil.txt
COPY --from=wsi_service_build /wsi-service/wsi_service_base_plugins/tifffile/requirements.txt /artifacts/requirements_tiffile.txt
RUN pip install -r /artifacts/requirements_tiffile.txt
COPY --from=wsi_service_build /wsi-service/wsi_service_base_plugins/tiffslide/requirements.txt /artifacts/requirements_tiffslide.txt
RUN pip install -r /artifacts/requirements_tiffslide.txt
COPY --from=wsi_service_build /wsi-service/wsi_service_base_plugins/wsidicom/requirements.txt /artifacts/requirements_wsidicom.txt
RUN pip install -r /artifacts/requirements_wsidicom.txt

COPY --from=wsi_service_build /wsi-service/dist/ /wsi-service/dist/
COPY --from=wsi_service_build /wsi-service/wsi_service_base_plugins/openslide/dist/ /wsi-service/dist/
COPY --from=wsi_service_build /wsi-service/wsi_service_base_plugins/pil/dist/ /wsi-service/dist/
COPY --from=wsi_service_build /wsi-service/wsi_service_base_plugins/tifffile/dist/ /wsi-service/dist/
COPY --from=wsi_service_build /wsi-service/wsi_service_base_plugins/tiffslide/dist/ /wsi-service/dist/
COPY --from=wsi_service_build /wsi-service/wsi_service_base_plugins/wsidicom/dist/ /wsi-service/dist/

RUN pip3 install /wsi-service/dist/*.whl

RUN mkdir /data


FROM ubuntu:22.04@sha256:c9cf959fd83770dfdefd8fb42cfef0761432af36a764c077aed54bbc5bb25368 AS wsi_service_production

RUN apt-get update \
  && apt-get install --no-install-recommends -y python3 python3-pip python3-packaging tini nano rsync curl \
  && rm -rf /var/lib/apt/lists/* \
  && adduser --disabled-password --gecos '' appuser \
  && mkdir /artifacts && chown appuser:appuser /artifacts \
  && mkdir -p /opt/app/bin && chown appuser:appuser /opt/app/bin

COPY --chown=appuser --from=wsi_service_intermediate /usr/local/lib/python3.10/dist-packages/ /usr/local/lib/python3.10/dist-packages/
COPY --chown=appuser --from=wsi_service_intermediate /data /data

COPY ./build_standalone/requirements.txt /tmp/requirements.txt
COPY --chown=appuser ./build_standalone/run.sh /usr/local/lib/python3.10/dist-packages/wsi_service

RUN pip3 install -r /tmp/requirements.txt \
  && chown appuser -R /usr/local/lib/python3.10/dist-packages/wsi_service \
  && chmod a+x /usr/local/lib/python3.10/dist-packages/wsi_service/run.sh
#USER appuser

ENV WEB_CONCURRENCY=8

EXPOSE 8080/tcp

WORKDIR /usr/local/lib/python3.10/dist-packages/wsi_service

# TODO move openslide build elsewhere to avoid expensive task last
RUN apt-get update && apt-get install --no-install-recommends -y \
    build-essential meson ninja-build zlib1g-dev libzstd-dev libpng-dev \
    libjpeg-dev libtiff-dev libopenjp2-7-dev libgdk-pixbuf2.0-dev \
    libxml2-dev sqlite3 libsqlite3-dev libcairo2-dev libglib2.0-dev libdcmtk-dev \
    libjpeg-turbo8-dev libzstd-dev libjxr-dev cmake git checkinstall

# We currently use a forked version of openslide, once this is merged to openslide, adjust the
# Dockerfile to use the original source including dynamic versioning

# Building from branch not original source
# https://github.com/openslide/openslide/pull/605
RUN git clone https://github.com/iewchen/openslide.git /openslide-lib \
  && cd /openslide-lib \
  && meson setup builddir \
  && meson compile -C builddir \
  && meson install -C builddir

COPY --chown=appuser ./build_standalone/gunicorn_conf.py .

ENTRYPOINT ["/usr/bin/tini", "--", "./run.sh"]

LABEL org.opencontainers.image.source="https://github.com/rationAI/WSI-Service"
