FROM python:3.7-stretch AS build

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1 \
  PYTHONDONTWRITEBYTECODE=1 \
  PIP_NO_CACHE_DIR=off \
  PIP_DISABLE_PIP_VERSION_CHECK=on \
  POETRY_HOME="/opt/poetry" \
  POETRY_VIRTUALENVS_IN_PROJECT=true \
  POETRY_NO_INTERACTION=1 \
  PYSETUP_PATH="/opt/pysetup" \
  VENV_PATH="/opt/pysetup/.venv"

ENV PATH="$POETRY_HOME/bin:$VENV_PATH/bin:$PATH"


RUN apt-get update \
  && apt-get install --no-install-recommends -y \
  python3-openslide
RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python
RUN which poetry

WORKDIR $PYSETUP_PATH
COPY ./wsi_service/poetry.lock ./wsi_service/pyproject.toml ./
RUN poetry install --no-dev 

WORKDIR /
ADD . /wsi_service
# RUN pip3 install -e /wsi_service

RUN mkdir /openslide_deps
RUN cp /usr/lib/x86_64-linux-gnu/libopenslide.so.0 /openslide_deps
RUN ldd /usr/lib/x86_64-linux-gnu/libopenslide.so.0 \
  | grep "=> /" | awk '{print $3}' | xargs -I '{}' cp -v '{}' /openslide_deps

RUN mkdir /data

FROM gcr.io/distroless/python3-debian10
ENV PYTHONUNBUFFERED=1 \
  PYTHONDONTWRITEBYTECODE=1 \
  PIP_NO_CACHE_DIR=off \
  PIP_DISABLE_PIP_VERSION_CHECK=on \
  POETRY_HOME="/opt/poetry" \
  POETRY_VIRTUALENVS_IN_PROJECT=true \
  POETRY_NO_INTERACTION=1 \
  PYSETUP_PATH="/opt/pysetup" \
  VENV_PATH="/opt/pysetup/.venv"

COPY --from=build /usr/local/lib/python3.7/site-packages/ /usr/lib/python3.7/.
COPY --from=build /openslide_deps/* /usr/lib/x86_64-linux-gnu/
COPY --from=build $POETRY_HOME $POETRY_HOME
COPY --from=build $PYSETUP_PATH $PYSETUP_PATH

ENV PATH="$POETRY_HOME/bin:$VENV_PATH/bin:$PATH"

COPY --from=build /wsi_service /wsi_service
# RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python

COPY --from=build /data /data
VOLUME ["/data"]

EXPOSE 8080/tcp
WORKDIR /wsi_service
ENTRYPOINT ["/opt/poetry/bin/poetry", "python", "-m", "wsi_service", "--port", "8080", "/data"]