FROM ubuntu:18.04 as build0

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
&& apt-get install -y python3-pip python3-dev curl \
&& cd /usr/local/bin \
&& ln -s /usr/bin/python3 python \
&& pip3 install --upgrade pip

RUN curl -fsSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python3

COPY isyntax_backend /root/isyntax/isyntax_backend
COPY pyproject.toml /root/isyntax
WORKDIR /root/isyntax

ENV PATH="${PATH}:/root/.poetry/bin"

RUN poetry lock
RUN poetry export --without-hashes -f requirements.txt > requirements.txt
RUN poetry build

FROM ubuntu:18.04 

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get clean && apt-get update \
&& apt-get install -y python3-pip python3-dev python3-wheel unzip

COPY philips-pathologysdk-2.0-ubuntu18_04_py36_research.zip /root/isyntax/philips-pathologysdk-2.0-ubuntu18_04_py36_research.zip

WORKDIR /root/isyntax

RUN unzip philips-pathologysdk-2.0-ubuntu18_04_py36_research.zip \
&& cd philips-pathologysdk-2.0-ubuntu18_04_py36_research \
&& chmod 777 InstallPathologySDK.sh \
&& ./InstallPathologySDK.sh py3 -y \
&& cd .. \
&& rm -r philips-pathologysdk-2.0-ubuntu18_04_py36_research

COPY --from=build0 /root/isyntax/requirements.txt /tmp
RUN pip3 install -r /tmp/requirements.txt

COPY --from=build0 /root/isyntax/dist/*.whl /tmp
RUN pip3 install /tmp/*.whl

RUN mkdir /data

CMD ["python3", "-m", "isyntax_backend"]
