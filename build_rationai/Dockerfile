ARG DEPLOY_FOLDER=build_rationai
FROM cerit.io/rationai/production/build-runner:v0.0.1 AS wsi_service_build

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

WORKDIR /wsi-service/wsi_service_base_plugins/tifffile_generic
RUN poetry build && poetry export -f requirements.txt > requirements.txt


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
COPY --from=wsi_service_build /wsi-service/wsi_service_base_plugins/tifffile_generic/requirements.txt /artifacts/requirements_tiffile_generic.txt
RUN pip install -r /artifacts/requirements_tiffile_generic.txt

COPY --from=wsi_service_build /wsi-service/dist/ /wsi-service/dist/
COPY --from=wsi_service_build /wsi-service/wsi_service_base_plugins/openslide/dist/ /wsi-service/dist/
COPY --from=wsi_service_build /wsi-service/wsi_service_base_plugins/pil/dist/ /wsi-service/dist/
COPY --from=wsi_service_build /wsi-service/wsi_service_base_plugins/tifffile/dist/ /wsi-service/dist/
COPY --from=wsi_service_build /wsi-service/wsi_service_base_plugins/tiffslide/dist/ /wsi-service/dist/
COPY --from=wsi_service_build /wsi-service/wsi_service_base_plugins/wsidicom/dist/ /wsi-service/dist/
COPY --from=wsi_service_build /wsi-service/wsi_service_base_plugins/tifffile_generic/dist/ /wsi-service/dist/

RUN pip3 install /wsi-service/dist/*.whl

RUN mkdir /data



FROM wsi_service_build AS wsi_service_dev

WORKDIR /wsi-service
RUN poetry install



FROM ubuntu:22.04@sha256:c9cf959fd83770dfdefd8fb42cfef0761432af36a764c077aed54bbc5bb25368 AS wsi_service_production
ARG DEPLOY_FOLDER

COPY --chown=www-data --from=wsi_service_build /openslide_deps/* /usr/lib/x86_64-linux-gnu/
COPY --chown=www-data --from=wsi_service_intermediate /usr/local/lib/python3.10/dist-packages/ /usr/local/lib/python3.10/dist-packages/
COPY --chown=www-data --from=wsi_service_intermediate /data /data
COPY --chown=www-data ${DEPLOY_FOLDER}/pod.run.sh /usr/local/lib/python3.10/dist-packages/wsi_service

RUN apt-get update \
  && apt-get install --no-install-recommends -y python3 python3-pip python3-packaging tini curl nano \
  && rm -rf /var/lib/apt/lists/* \
  && usermod --non-unique --uid 1000 www-data \
  && mkdir /artifacts && chown www-data:www-data /artifacts \
  && mkdir -p /opt/app/bin && chown www-data:www-data /opt/app/bin \
  && chmod u+x /usr/local/lib/python3.10/dist-packages/wsi_service/pod.run.sh \
  && chown www-data -R /usr/local/lib/python3.10/dist-packages/wsi_service \
  && mkdir -p modules
EXPOSE 8080/tcp
ENV WEB_CONCURRENCY=8

WORKDIR /usr/local/lib/python3.10/dist-packages/wsi_service
COPY --chown=www-data ./build_rationai/*.env .
#USER www-data
ENTRYPOINT ["./pod.run.sh"]
