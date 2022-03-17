FROM registry.gitlab.com/empaia/integration/ci-docker-images/test-runner@sha256:447581003eb7f78b488e6a7accb23dac93e8be38d21ee424af3bef25564f1cc1 AS wsi_service_build

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
  && apt-get install --no-install-recommends -y \
  python3-openslide

RUN mkdir /openslide_deps
RUN cp /usr/lib/x86_64-linux-gnu/libopenslide.so.0 /openslide_deps
RUN ldd /usr/lib/x86_64-linux-gnu/libopenslide.so.0 \
  | grep "=> /" | awk '{print $3}' | xargs -I '{}' cp -v '{}' /openslide_deps

RUN curl -o /tmp/libpixman-1-0_0.40.0-1build3_amd64.deb \
  http://launchpadlibrarian.net/562429593/libpixman-1-0_0.40.0-1build3_amd64.deb
RUN dpkg -i /tmp/libpixman-1-0_0.40.0-1build3_amd64.deb
ENV LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libpixman-1.so.0.40.0

COPY . /wsi-service

WORKDIR /wsi-service
RUN poetry build

WORKDIR /wsi-service/wsi_service_base_plugins/tifffile
RUN poetry build

WORKDIR /wsi-service/wsi_service_base_plugins/openslide
RUN poetry build

WORKDIR /wsi-service/wsi_service_base_plugins/pil
RUN poetry build


FROM wsi_service_build AS wsi_service_dev

WORKDIR /wsi-service
RUN poetry install


FROM registry.gitlab.com/empaia/integration/ci-docker-images/test-runner@sha256:447581003eb7f78b488e6a7accb23dac93e8be38d21ee424af3bef25564f1cc1 AS wsi_service_intermediate

COPY --from=wsi_service_build /wsi-service/dist/ /wsi-service/dist/
COPY --from=wsi_service_build /wsi-service/wsi_service_base_plugins/openslide/dist/ /wsi-service/dist/
COPY --from=wsi_service_build /wsi-service/wsi_service_base_plugins/pil/dist/ /wsi-service/dist/
COPY --from=wsi_service_build /wsi-service/wsi_service_base_plugins/tifffile/dist/ /wsi-service/dist/

RUN pip3 install /wsi-service/dist/*.whl

RUN mkdir /data


FROM registry.gitlab.com/empaia/integration/ci-docker-images/python-base@sha256:cdcaf42dcda64f2eb60ecfddaf491860aeff2a4bfdb42b4e546eb7ba282f83fb AS wsi_service_production

COPY --chown=appuser --from=wsi_service_build /openslide_deps/* /usr/lib/x86_64-linux-gnu/
COPY --chown=appuser --from=wsi_service_build /usr/lib/x86_64-linux-gnu/libpixman-1.so.0.40.0 /usr/lib/x86_64-linux-gnu/libpixman-1.so.0.40.0
ENV LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libpixman-1.so.0.40.0

COPY --chown=appuser --from=wsi_service_intermediate /usr/local/lib/python3.8/dist-packages/ /usr/local/lib/python3.8/dist-packages/
COPY --chown=appuser --from=wsi_service_intermediate /data /data

ENV WEB_CONCURRENCY=8

EXPOSE 8080/tcp

WORKDIR /usr/local/lib/python3.8/dist-packages/wsi_service

CMD ["python3", "-m", "uvicorn", "wsi_service.api:api", "--host", "0.0.0.0", "--port", "8080", "--loop=uvloop", "--http=httptools"]
