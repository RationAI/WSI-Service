FROM ubuntu:18.04 as build0

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

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

RUN apt-get clean && apt-get update \
    && apt-get install -y python3-pip python3-dev curl unzip

RUN pip3 install wheel

COPY --from=build0 /root/isyntax/requirements.txt /tmp
RUN pip3 install -r /tmp/requirements.txt

COPY --from=build0 /root/isyntax/dist/*.whl /tmp
RUN pip3 install /tmp/*.whl

RUN curl -o philips-sdk.zip https://nextcloud.empaia.org/s/Lk6rR9gBre2dDW5/download
RUN unzip philips-sdk.zip -d .
RUN cd philips-pathologysdk-2.0-ubuntu18_04_py36_research && chmod 777 InstallPathologySDK.sh && ./InstallPathologySDK.sh py3 -y

COPY . /root/isyntax
WORKDIR /root/isyntax/backend

RUN mkdir /data

EXPOSE 5556/tcp

ENTRYPOINT ["python3", "-m", "backend.__main__", "--ip", "127.0.0.1", "--port", "5556"]