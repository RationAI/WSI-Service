ARG DEPLOY_FOLDER=build_rationai
FROM registry.gitlab.com/empaia/integration/ci-docker-images/test-runner:0.4.11@sha256:a9a05dc857152268cc06ce7c8a2da338921eba66299744b83b21590160f57064 AS wsi_service_build

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


FROM registry.gitlab.com/empaia/integration/ci-docker-images/python-base:0.3.8@sha256:c1a82816aef0f5e2ff605843df0bb2c41bc1bf5df1bec2c2fe9532874f53a9d0 AS wsi_service_intermediate

USER root
RUN apt-get update \
  && apt-get install --no-install-recommends -y build-essential python3-pip python3-dev \
  && rm -rf /var/lib/apt/lists/*

COPY --from=wsi_service_build /wsi-service/requirements.txt /artifacts
RUN pip install -r /artifacts/requirements.txt --break-system-packages

COPY --from=wsi_service_build /wsi-service/wsi_service_base_plugins/openslide/requirements.txt /artifacts/requirements_openslide.txt
RUN pip install -r /artifacts/requirements_openslide.txt --break-system-packages
COPY --from=wsi_service_build /wsi-service/wsi_service_base_plugins/pil/requirements.txt /artifacts/requirements_pil.txt
RUN pip install -r /artifacts/requirements_pil.txt --break-system-packages
COPY --from=wsi_service_build /wsi-service/wsi_service_base_plugins/tifffile/requirements.txt /artifacts/requirements_tiffile.txt
RUN pip install -r /artifacts/requirements_tiffile.txt --break-system-packages
COPY --from=wsi_service_build /wsi-service/wsi_service_base_plugins/tiffslide/requirements.txt /artifacts/requirements_tiffslide.txt
RUN pip install -r /artifacts/requirements_tiffslide.txt --break-system-packages
COPY --from=wsi_service_build /wsi-service/wsi_service_base_plugins/wsidicom/requirements.txt /artifacts/requirements_wsidicom.txt
RUN pip install -r /artifacts/requirements_wsidicom.txt --break-system-packages

COPY --from=wsi_service_build /wsi-service/dist/ /wsi-service/dist/
COPY --from=wsi_service_build /wsi-service/wsi_service_base_plugins/openslide/dist/ /wsi-service/dist/
COPY --from=wsi_service_build /wsi-service/wsi_service_base_plugins/pil/dist/ /wsi-service/dist/
COPY --from=wsi_service_build /wsi-service/wsi_service_base_plugins/tifffile/dist/ /wsi-service/dist/
COPY --from=wsi_service_build /wsi-service/wsi_service_base_plugins/tiffslide/dist/ /wsi-service/dist/
COPY --from=wsi_service_build /wsi-service/wsi_service_base_plugins/wsidicom/dist/ /wsi-service/dist/

RUN pip3 install /wsi-service/dist/*.whl --break-system-packages



FROM wsi_service_build AS wsi_service_dev

WORKDIR /wsi-service
RUN poetry install



FROM registry.gitlab.com/empaia/integration/ci-docker-images/python-base:0.3.8@sha256:c1a82816aef0f5e2ff605843df0bb2c41bc1bf5df1bec2c2fe9532874f53a9d0 AS wsi_service_production
ARG DEPLOY_FOLDER
USER root

COPY --chown=appuser --from=wsi_service_intermediate /usr/local/lib/python3.12/dist-packages/ /usr/local/lib/python3.12/dist-packages/
COPY --chown=appuser ${DEPLOY_FOLDER}/pod.run.sh /usr/local/lib/python3.12/dist-packages/wsi_service

RUN apt-get update \
  && apt-get install --no-install-recommends -y python3 python3-pip tini curl nano \
  && rm -rf /var/lib/apt/lists/* \
  && mkdir -p /opt/app/bin && chown appuser:appuser /opt/app/bin \
  && chmod a+x /usr/local/lib/python3.12/dist-packages/wsi_service/pod.run.sh \
  && chown appuser -R /usr/local/lib/python3.12/dist-packages/wsi_service \
  && mkdir -p modules
EXPOSE 8080/tcp
ENV WEB_CONCURRENCY=8

WORKDIR /usr/local/lib/python3.12/dist-packages/wsi_service

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

COPY --chown=appuser ./build_rationai/*.env .
USER appuser
ENTRYPOINT ["./pod.run.sh"]
