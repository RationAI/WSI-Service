FROM ubuntu:18.04 as build0

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
ARG ISX_PHILIPS_SDK_FILEPATH

RUN apt-get update \
    && apt-get install -y python3-pip python3-dev curl \
    && cd /usr/local/bin \
    && ln -s /usr/bin/python3 python \
    && pip3 install --upgrade pip

RUN curl -fsSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python3

COPY . /root/isyntax
WORKDIR /root/isyntax

ENV PATH="${PATH}:/root/.poetry/bin"

RUN poetry lock
RUN poetry export --without-hashes -f requirements.txt > requirements.txt
RUN poetry build

FROM ubuntu:18.04 

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
ARG ISX_PHILIPS_SDK_FILEPATH

RUN apt-get clean && apt-get update \
    && apt-get install -y python3-pip python3-dev curl p7zip-full

RUN pip3 install wheel

COPY --from=build0 /root/isyntax/requirements.txt /tmp
RUN pip3 install -r /tmp/requirements.txt

COPY --from=build0 /root/isyntax/dist/*.whl /tmp
RUN pip3 install /tmp/*.whl

COPY . /root/isyntax
RUN 7z x /root/isyntax/$ISX_PHILIPS_SDK_FILEPATH -o/root/isyntax/

RUN cd /root/isyntax/philips-pathologysdk-2.0-ubuntu18_04_py36_research \
    && chmod 777 InstallPathologySDK.sh \
    && ./InstallPathologySDK.sh py3 -y

RUN rm -rf /root/isyntax/$ISX_PHILIPS_SDK_FILEPATH
RUN rm -rf /root/isyntax/philips-pathologysdk-2.0-ubuntu18_04_py36_research

WORKDIR /root/isyntax/backend

RUN mkdir /data

EXPOSE 5556/tcp

ENTRYPOINT ["python3", "-m", "backend.__main__"]