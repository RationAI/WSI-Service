# wsi-service

implementation of the EMPAIA WSI-Service to stream whole slide images tile-based via HTTP

## How to run
WSI-Service is a python module and can be run either locally or via docker.

### Run local 
Install using pip. Start via
```
python3 -m wsi_service [OPTIONS] data_dir

positional arguments:
  data_dir             path to histo data, should point to directory with
                       folders as cases

optional arguments:
  -h, --help           show this help message and exit
  --port PORT          Port the WSI-Service listens to
  --debug              Use the debug config
  --load-example-data  This will download an example image into the data
                       folder before starting the server

```

### Run as Docker
Build (or download turnkey ready) the docker image
```
cd PATH_OF_DOCKERFILE
docker build -t wsi-service .
```

Run the docker image, for example:
```
docker run \
  -p 8080:8080 \
  -u $(id -u ${USER}):$(id -g ${USER}) \
  --rm \
  -v PATH_TO_DATA_DIR_ON_HOST:/data \
  -v PATH_TO_REPOSITORY_ROOT:/wsi_service \
  wsi-service \
    --load-example-data \
```

Short explanation of the parameters used:

* ```-p 8080:8080``` forward the port
* ```-u $(id -u ${USER}):$(id -g ${USER})``` recommendet, runs container with current user instead of root
* ```--rm``` optional, remove if container should be reused (recommended)
* ```-v PATH_TO_DATA_DIR_ON_HOST:/data``` optional, if not set, empty dir will be used. Make sure container user (-u) has read access
* ```-v PATH_TO_REPOSITORY_ROOT:/wsi_service``` optional, will use the source code of host and automatically restart server on changes
* ```--load-example-data``` optional, add (more) python parameters here as shown above


# TODO

* gitlab ci -> Docker to registry
* pass-through tiles