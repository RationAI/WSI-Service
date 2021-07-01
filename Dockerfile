FROM python:3.9 AS wsi_service_dev

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
  && apt-get install --no-install-recommends -y \
  curl python3-openslide

RUN mkdir /openslide_deps
RUN cp /usr/lib/x86_64-linux-gnu/libopenslide.so.0 /openslide_deps
RUN ldd /usr/lib/x86_64-linux-gnu/libopenslide.so.0 \
  | grep "=> /" | awk '{print $3}' | xargs -I '{}' cp -v '{}' /openslide_deps

RUN curl https://www.cairographics.org/releases/pixman-0.40.0.tar.gz | tar -xz
RUN cd pixman-0.40.0 && ./configure && make && make install
ENV LD_PRELOAD=/usr/local/lib/libpixman-1.so.0.40.0

RUN pip3 install poetry

COPY . /wsi-service

WORKDIR /wsi-service
RUN poetry build

WORKDIR /wsi-service/wsi_service_base_plugins/tifffile
RUN poetry build

WORKDIR /wsi-service/wsi_service_base_plugins/openslide
RUN poetry build

WORKDIR /wsi-service
RUN poetry install


FROM python:3.9 AS wsi_service_intermediate

COPY --from=wsi_service_dev /wsi-service/dist/ /wsi-service/dist/
COPY --from=wsi_service_dev /wsi-service/wsi_service_base_plugins/openslide/dist/ /wsi-service/dist/
COPY --from=wsi_service_dev /wsi-service/wsi_service_base_plugins/tifffile/dist/ /wsi-service/dist/

RUN pip3 install /wsi-service/dist/*.whl


FROM python:3.9-slim AS wsi_servie_production

RUN pip3 install uvicorn

COPY --from=wsi_service_dev /openslide_deps/* /usr/lib/x86_64-linux-gnu/
COPY --from=wsi_service_dev /usr/local/lib/libpixman-1.so.0.40.0 /usr/local/lib/libpixman-1.so.0.40.0
ENV LD_PRELOAD=/usr/local/lib/libpixman-1.so.0.40.0

COPY --from=wsi_service_intermediate /usr/local/lib/python3.9/site-packages/ /usr/local/lib/python3.9/site-packages/

RUN mkdir /data

WORKDIR /usr/local/lib/python3.9/site-packages/wsi_service/

ENV WEB_CONCURRENCY=8

EXPOSE 8080/tcp