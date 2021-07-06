# WSI Service

EMPAIA WSI Service to stream whole slide images

## Overview

The *WSI Service* enables users to stream Whole Slide Images (WSI) tile-based via HTTP. It is based on a FastAPI webserver and a number of [plugins]([plugin-development](plugin-development)) to access whole slide image data.

Regarding the slide's metadata, it provides the extent of the base level (original image, level=0), its pixel size in nm (level=0), general tile extent, the total count of levels and a list of levels with information about its extent, downsampling factor in relation to the base level. Furthermore, the channel depth is given along with a list of all available channels.

Regions of the WSI can be requested on any of the available levels. There is also a way to access tiles of a predefined size of each level (e.g. useful for a [viewer](wsi_service/viewer.html)). Furthermore, it is possible to get a thumbnail, label and macro image.

There are several endpoints made available by this service:

- `GET /v1/slides/{slide_id}/info` - Get slide info
- `GET /v1/slides/{slide_id}/region/level/{level}/start/{start_x}/{start_y}/size/{size_x}/{size_y}` - Get slide region
- `GET /v1/slides/{slide_id}/tile/level/{level}/tile/{tile_x}/{tile_y}` - Get slide tile
- `GET /v1/slides/{slide_id}/thumbnail/max_size/{max_x}/{max_y}` - Get slide thumbnail image
- `GET /v1/slides/{slide_id}/label/max_size/{max_x}/{max_y}` - Get slide label image
- `GET /v1/slides/{slide_id}/macro/max_size/{max_x}/{max_y}` - Get slide macro image

The last five endpoints all return image data. The image format and its quality (e.g. for jpeg) can be selected. Formats include jpeg, png, tiff, bmp, gif.

When tiff is specified as output format for the region and tile endpoint the raw data of the image is returned. This is paricularly important for images with abitrary image channels and channels with a higher color depth than 8bit (e.g. fluorescence images). The channel composition of the image can be obtained through the slide info endpoint, where the dedicated channels are listed along with its color, name and bitness. Multi-channel images can also be represented as RGB-images (mostly for displaying reasons in the viewer). Note that the mapping of all color channels to RGB values is currently restricted to the first three channels. Single channels (or multiple channels) can be retrieved through the optional parameter image_channels as an integer array referencing the channel IDs.

The region and the tile endpoint also offer the selection of a layer with the index z in a Z-Stack.

### Standalone version

The WSI Service relies on the [Storage Mapper Service](https://gitlab.cc-asp.fraunhofer.de/empaia/platform/data/storage-mapper-service) to get storage information for a certain slide ID. If the mapper-address is not provided (see [How to run](how-to-run)), the WSI Service will be run in standalone mode using a local mapper. This local mapper fulfills the function of the storage mapper service, the id mapper service and part of the clinical data service by creating case ids for folders found in the data folder and slide ids for images within these case folders. In the standalone mode there are few additional endpoints, which can be accessed:

- `GET /v1/cases/` - Get cases
- `GET /v1/cases/{case_id}/slides/` - Get available slides
- `GET /v1/slides/{slide_id}` - Get slide
- `GET /v1/slides/{slide_id}/storage` - Get slide storage information

Two viewer endpoints are also made available by the standalone version:

- Validation Viewer: [http://localhost:8080/v1/validation_viewer](http://localhost:8080/v1/validation_viewer)

- Simple Viewer: [http://localhost:8080/v1/slides/{slide_id}/viewer](http://localhost:8080/v1/slides/{slide_id}/viewer)

### Supported formats

Different formats are supported by plugins for accessing image data. Two base plugins are included and support the following formats:

- [openslide](./wsi_service_base_plugins/openslide/)
  - 3DHISTECH (\*.mrxs)
  - APERIO (\*.svs)
  - GENERIC TIF (\*.tif / \*.tiff)
  - HAMAMATSU (\*.ndpi)
  - Partially supported:
    - LEICA (\*.scn)
    - VENTANA (\*.bif)

- [tiffile](./wsi_service_base_plugins/tifffile/)
  - OME-TIFF (\*.ome.tif, \*.ome.tif, \*.ome.tiff, \*.ome.tf2, \*.ome.tf8, \*.ome.btf)

## How to run

WSI Service is a python module and has to be run via docker.

### Run locally

Make sure [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) is installed.

Set environment variables in your shell or in a `.env` file:

```bash
WS_CORS_ALLOW_ORIGINS=["*"]
WS_DISABLE_OPENAPI=False
WS_MAPPER_ADDRESS=http://localhost:8080/v1/slides/{slide_id}/storage
WS_LOCAL_MODE=True
WS_INACTIVE_HISTO_IMAGE_TIMEOUT_SECONDS=600
WS_MAX_RETURNED_REGION_SIZE=25000000
WS_ROOT_PATH=

COMPOSE_RESTART=no
COMPOSE_NETWORK=default
COMPOSE_WS_PORT=8080
COMPOSE_DATA_DIR=/data
```

Short explanation of the parameters used:

- `WS_CORS_ALLOW_ORIGINS` allow cors for different origins
- `WS_DISABLE_OPENAPI` disable swagger api documentation (`/docs`)
- `WS_MAPPER_ADDRESS` storage mapper service address
- `WS_LOCAL_MODE` when set to true, wsi service is started in local mode
- `WS_INACTIVE_HISTO_IMAGE_TIMEOUT_SECONDS` set timeout for inactive histo images (default is 600 seconds)
- `WS_MAX_RETURNED_REGION_SIZE` set maximum image region size for service (channels * width * height; default is 4 * 5000 * 5000)
  
- `COMPOSE_RESTART` set to `no`, `always` to configure restart settings
- `COMPOSE_NETWORK` set network used for wsi service
- `COMPOSE_WS_PORT` set external port for wsi service
- `COMPOSE_DATA_DIR` mounted volume to the image data (e.g. `/testdata/OpenSlide_adapted`)

Then run

```bash
docker-compose up --build
```

It is not recommened to run the python package outside the specified docker image due to issues with library dependencies on different platforms.

## Development

Run

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

### Run tests

Run while development composition is up and running:

```bash
docker exec -it wsi-service_wsi_service_1 poetry run pytest --cov wsi_service
```

To run tests locally, make sure you have the latest [**testdata**](https://nextcloud.empaia.org/f/188182) (For access contact project maintainer).

After downloading the testdata, set the path of the `OpenSlide_adapted` folder as environment variable in your `.env` file:

```bash
COMPOSE_DATA_DIR=/testdata/OpenSlide_adapted
```

### Run debugging

Use VS Code to start `Python: Remote Attach` while development composition is up and running.

### Run static code analysis and fix issues

If you are using VS Code there are already default [settings](https://gitlab.cc-asp.fraunhofer.de/empaia/platform/data/wsi-service/-/blob/master/.vscode/settings.json) that will sort your imports and reformat the code on save. Furthermore, there will be standard pylint warnings from VS Code that should be fixed manually.

To start the automatic formatter from console run

```bash
black .
```

To start the automatic import sorter from console run

```bash
isort . --profile black
```

To start pylint from console run

```bash
pylint wsi_service --disable=all --enable=F,E,unreachable,duplicate-key,unnecessary-semicolon,global-variable-not-assigned,unused-variable,binary-op-exception,bad-format-string,anomalous-backslash-in-string,bad-open-mode --extension-pkg-whitelist=pydantic
```

following [VS Code](https://code.visualstudio.com/docs/python/linting#_default-pylint-rules).

## Plugin development

Plugins are python packages following the naming scheme `wsi-service-plugin-PLUGINNAME` that need to implement a Slide class following the base class in [`slide.py`](wsi_service/slide.py). Additionally, there needs to be an `__init__.py` file like this:

```python
from .slide import Slide

supported_file_extensions = [
    ".tif"
]

def open(filepath, slide_id=0):
    return Slide(filepath, slide_id)
```

Once these minimal requirements are taken care of, the python package can be installed on top of an existing  WSI Service docker image by simple running a Dockerfile along these lines:

```Dockerfile
FROM registry.gitlab.cc-asp.fraunhofer.de:4567/empaia/platform/data/wsi-service

COPY wsi-service-plugin-PLUGINNAME.whl /tmp/wsi-service-plugin-PLUGINNAME.whl

RUN pip3 install /tmp/wsi-service-plugin-PLUGINNAME.whl
```

There are two base plugins ([openslide](./wsi_service_base_plugins/openslide/), [tiffile](./wsi_service_base_plugins/tifffile/)) that can be used as templates for new plugins. Additionally to the mentioned minimal requirements these plugins use poetry to manage and create the python package. This is highly recommended when creating a plugin. Furthermore, these plugins implement tests based on pytest by defining a number of parameters on top of example integration test functions defined as part of the WSI Service ([plugin_example_tests](./wsi_service/tests/integration/plugin_example_tests)). 

A more complete example of an external plugin integration can be found in the iSyntax integration repository ([wsi-service-plugin-isyntax](https://gitlab.cc-asp.fraunhofer.de/empaia/platform/data/wsi-service-plugins/wsi-service-plugin-isyntax)). That example includes the usage of an external service that is run in an additional docker container due to runtime limitations.
