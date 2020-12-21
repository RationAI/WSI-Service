FROM python:3.8 AS build_0

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
  && apt-get install --no-install-recommends -y \
  python3-openslide

RUN mkdir /openslide_deps
RUN cp /usr/lib/x86_64-linux-gnu/libopenslide.so.0 /openslide_deps
RUN ldd /usr/lib/x86_64-linux-gnu/libopenslide.so.0 \
  | grep "=> /" | awk '{print $3}' | xargs -I '{}' cp -v '{}' /openslide_deps

RUN pip3 install poetry

COPY . /wsi_service
WORKDIR /wsi_service

RUN poetry build
RUN poetry export --dev --without-hashes --output requirements_dev.txt


FROM python:3.8 AS build_1

COPY --from=build_0 /openslide_deps/* /usr/lib/x86_64-linux-gnu/
COPY --from=build_0 /wsi_service/dist/ /wsi_service/dist/

RUN pip3 install /wsi_service/dist/*.whl


FROM python:3.8-slim

COPY --from=build_0 /openslide_deps/* /usr/lib/x86_64-linux-gnu/
COPY --from=build_1 /usr/local/lib/python3.8/site-packages/ /usr/local/lib/python3.8/site-packages/

COPY --from=build_0 /wsi_service/requirements_dev.txt /usr/local/lib/python3.8/site-packages/wsi_service/requirements_dev.txt
WORKDIR /usr/local/lib/python3.8/site-packages/wsi_service/

RUN mkdir /data

EXPOSE 8080/tcp
ENTRYPOINT ["python", "-m", "wsi_service", "--port", "8080", "/data"]
