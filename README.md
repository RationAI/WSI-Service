# WSI Service

Implementation of the EMPAIA WSI Service to stream whole slide images tile-based via HTTP

## How to run
WSI Service is a python module and can be run either locally or via docker.

### Run locally
Make sure [OpenSlide](https://openslide.org/download/) is installed. Install WSI Service by running the following line within this folder
```
pip3 install -e .
```

Start via
```
python3 -m wsi_service [OPTIONS] data_dir

positional arguments:
  data_dir             Base path to histo data

optional arguments:
  -h, --help           Show this help message and exit
  --port PORT          Port the WSI Service listens to
  --debug              Use the debug config
  --load-example-data  This will download an example image into the data
                       folder before starting the server
  --mapper-address     Mapper-Service Address
```
Afterwards, visit http://localhost:8080

### Run with docker
Download the turnkey ready docker image
```
docker pull registry.gitlab.cc-asp.fraunhofer.de:4567/empaia/platform/data/wsi-service
```

or build the docker image yourself from source
```
cd PATH_OF_DOCKERFILE
docker build -t registry.gitlab.cc-asp.fraunhofer.de:4567/empaia/platform/data/wsi-service .
```
Of course, it can be tagged e.g. with only *wsi-service*, here the tag is just used for consitency with following commands.

Run the docker image, for example (minimal test):
```
docker run -it --rm -p 8080:8080 registry.gitlab.cc-asp.fraunhofer.de:4567/empaia/platform/data/wsi-service --load-example-data
```

Or with more options
```
docker run \
  -it \
  -p 8080:8080 \
  --rm \
  -v PATH_TO_DATA_DIR_ON_HOST:/data \
  -v PATH_TO_REPOSITORY_ROOT:/wsi_service \
  registry.gitlab.cc-asp.fraunhofer.de:4567/empaia/platform/data/wsi-service \
  --debug
```

Short explanation of the parameters used:

* ```-it``` initializes an interactive tty
* ```-p 8080:8080``` forward the port
* ```--rm``` optional, remove if container should be reused (recommended)
* ```-v PATH_TO_DATA_DIR_ON_HOST:/data``` optional, if not set, empty dir will be used. Make sure container user (-u) has read access
* ```-v PATH_TO_REPOSITORY_ROOT:/wsi_service``` optional, will use the source code of host and automatically restart server on changes
* ```--debug``` optional, use debug config and activate reload

Afterwards, visit http://localhost:8080


## Development

### Use debug to activate reload

Service is reloaded after code changes. Activate locally with
```
python3 -m wsi_service --debug data_dir
```
or using docker with
```
docker run \
  -it \
  -p 8080:8080 \
  --rm \
  -v PATH_TO_DATA_DIR_ON_HOST:/data \
  -v PATH_TO_REPOSITORY_ROOT:/wsi_service \
  registry.gitlab.cc-asp.fraunhofer.de:4567/empaia/platform/data/wsi-service \
  --debug
```

### Run tests 
```
pytest --pyargs wsi_service
```
or using docker with
```
docker run \
  -it \
  --rm \
  --entrypoint python3 \
  registry.gitlab.cc-asp.fraunhofer.de:4567/empaia/platform/data/wsi-service \
  -m pytest --pyargs wsi_service
```

### Run static code analysis and fix issues

If you are using VS Code there are already default [settings](https://gitlab.cc-asp.fraunhofer.de/empaia/platform/data/wsi-service/-/blob/6-add-tests-to-wsi-service/.vscode/settings.json) that will sort your imports and reformat the code on save. Furthermore, there will be standard pylint warnings from VS Code that should be fixed manually.

To start the automatic formatter from console run
```
black .
```

To start the automatic import sorter from console run
```
isort . --profile black
```

To start pylint from console run
```
pylint wsi_service --disable=all --enable=F,E,unreachable,duplicate-key,unnecessary-semicolon,global-variable-not-assigned,unused-variable,binary-op-exception,bad-format-string,anomalous-backslash-in-string,bad-open-mode --extension-pkg-whitelist=pydantic
```
following [VS Code](https://code.visualstudio.com/docs/python/linting#_default-pylint-rules).