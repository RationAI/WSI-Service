FROM registry.gitlab.com/empaia/integration/ci-docker-images/test-runner:0.2.8@sha256:0c20dd487c2bb040fd78991bf54f396cb1fd9ab314a7a55bee0ad4909748797d AS wsi_service_build
RUN apt-get update && apt-get install --no-install-recommends -y \
    build-essential meson ninja-build zlib1g-dev libzstd-dev libpng-dev \
    libjpeg-dev libtiff-dev libopenjp2-7-dev libgdk-pixbuf2.0-dev \
    libxml2-dev sqlite3 libsqlite3-dev libcairo2-dev libglib2.0-dev libdcmtk-dev \
    libjpeg-turbo8-dev libzstd-dev libjxr-dev cmake git checkinstall openjdk-17-jdk libffi-dev && \
    git config --global advice.detachedHead false && \
    git config --global --add url."https://github.com/".insteadOf git@github.com:

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH="$JAVA_HOME/bin:$PATH"
ENV POETRY_VIRTUALENVS_CREATE=false
ENV POETRY_NO_INTERACTION=1

#RUN pip install numpy==1.23.5 && python -m pip install --use-pep517 git+https://github.com/LeeKamentsky/python-javabridge \
#    && pip install --no-cache-dir JPype1==1.4.1 python-bioformats==4.1.0

# We currently use a forked version of openslide, once this is merged to openslide, adjust the
# Dockerfile to use the original source including dynamic versioning

# Building from branch not original source
# https://github.com/openslide/openslide/pull/605
RUN git clone https://github.com/iewchen/openslide.git /openslide-lib \
  && cd /openslide-lib \
  && meson setup builddir \
  && meson compile -C builddir \
  && meson install -C builddir

ENV DEBIAN_FRONTEND=noninteractive
ENV POETRY_VIRTUALENVS_CREATE=false
ENV POETRY_NO_INTERACTION=1

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

WORKDIR /wsi-service/wsi_service_base_plugins/bioio
RUN poetry build && poetry export -f requirements.txt > requirements.txt


# Todo dev image does not install properly requirements from plugins...
FROM wsi_service_build AS wsi_service_dev

WORKDIR /wsi-service
RUN poetry lock --no-update -vvv && poetry install --no-root

# Install dependencies for each plugin using Poetry
WORKDIR /wsi-service/wsi_service_base_plugins/openslide
RUN poetry install --no-root

WORKDIR /wsi-service/wsi_service_base_plugins/pil
RUN poetry install --no-root

WORKDIR /wsi-service/wsi_service_base_plugins/tifffile
RUN poetry install --no-root

WORKDIR /wsi-service/wsi_service_base_plugins/tiffslide
RUN poetry install --no-root

WORKDIR /wsi-service/wsi_service_base_plugins/wsidicom
RUN poetry install --no-root

WORKDIR /wsi-service/wsi_service_base_plugins/bioio
RUN poetry install --no-root

# Return to the main service
# LOCK + INSTALL after plugins are in place
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
COPY --from=wsi_service_build /wsi-service/wsi_service_base_plugins/bioio/requirements.txt /artifacts/requirements_bioio.txt
RUN pip install -r /artifacts/requirements_bioio.txt

COPY --from=wsi_service_build /wsi-service/dist/ /wsi-service/dist/
COPY --from=wsi_service_build /wsi-service/wsi_service_base_plugins/openslide/dist/ /wsi-service/dist/
COPY --from=wsi_service_build /wsi-service/wsi_service_base_plugins/pil/dist/ /wsi-service/dist/
COPY --from=wsi_service_build /wsi-service/wsi_service_base_plugins/tifffile/dist/ /wsi-service/dist/
COPY --from=wsi_service_build /wsi-service/wsi_service_base_plugins/tiffslide/dist/ /wsi-service/dist/
COPY --from=wsi_service_build /wsi-service/wsi_service_base_plugins/wsidicom/dist/ /wsi-service/dist/
COPY --from=wsi_service_build /wsi-service/wsi_service_base_plugins/bioio/dist/ /wsi-service/dist/

RUN pip3 install /wsi-service/dist/*.whl

RUN mkdir /data


FROM ubuntu:22.04@sha256:bcc511d82482900604524a8e8d64bf4c53b2461868dac55f4d04d660e61983cb AS wsi_service_production

RUN apt-get update \
  && apt-get install --no-install-recommends -y python3 python3-pip python3-packaging \
  && rm -rf /var/lib/apt/lists/*

RUN adduser --disabled-password --gecos '' appuser \
  && mkdir /artifacts && chown appuser:appuser /artifacts \
  && mkdir -p /opt/app/bin && chown appuser:appuser /opt/app/bin
USER appuser

COPY --chown=appuser --from=wsi_service_intermediate /usr/local/lib/python3.10/dist-packages/ /usr/local/lib/python3.10/dist-packages/
COPY --chown=appuser --from=wsi_service_intermediate /data /data

ENV WEB_CONCURRENCY=8

EXPOSE 8080/tcp

WORKDIR /usr/local/lib/python3.10/dist-packages/wsi_service

# TODO move openslide build elsewhere to avoid expensive task last
RUN apt-get update && apt-get install --no-install-recommends -y \
    build-essential meson ninja-build zlib1g-dev libzstd-dev libpng-dev \
    libjpeg-dev libtiff-dev libopenjp2-7-dev libgdk-pixbuf2.0-dev \
    libxml2-dev sqlite3 libsqlite3-dev libcairo2-dev libglib2.0-dev libdcmtk-dev \
    libjpeg-turbo8-dev libzstd-dev libjxr-dev cmake git checkinstall openjdk-17-jre-headless

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH="$JAVA_HOME/bin:$PATH"

# We currently use a forked version of openslide, once this is merged to openslide, adjust the
# Dockerfile to use the original source including dynamic versioning

# Building from branch not original source
# https://github.com/openslide/openslide/pull/605
RUN git clone https://github.com/iewchen/openslide.git /openslide-lib \
  && cd /openslide-lib \
  && meson setup builddir \
  && meson compile -C builddir \
  && meson install -C builddir

CMD ["python3", "-m", "uvicorn", "wsi_service.app:app", "--host", "0.0.0.0", "--port", "8080", "--loop=uvloop", "--http=httptools"]
