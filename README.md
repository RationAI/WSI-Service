# wsi-service

Implementation of the EMPAIA WSI-Service to stream whole slide images tile-based via HTTP

## How to run
WSI-Service is a python module and can be run either locally or via docker.

### Run local 
Make sure [OpenSlide](https://openslide.org/download/) is installed. Install using pip within this folder
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
  --port PORT          Port the WSI-Service listens to
  --debug              Use the debug config
  --load-example-data  This will download an example image into the data
                       folder before starting the server
  --mapper-address     Mapper-Service Address
```

### Run as Docker
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
* ```--debug``` optional, use debug config (parameters after the image name are passed to the python module)

Afterwards, visit http://localhost:8080

### Run tests 
```
pytest --pyargs wsi_service
```
or using Docker with
```
docker run \
  -it \
  --rm \
  --entrypoint python3 \
  registry.gitlab.cc-asp.fraunhofer.de:4567/empaia/platform/data/wsi-service \
  -m pytest --pyargs wsi_service
```