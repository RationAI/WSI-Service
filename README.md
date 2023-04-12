# WSI Service

## Quickstart

```bash
docker run -v <local-data-folder>:/data -p 8080:8080 --rm -d registry.gitlab.com/empaia/services/wsi-service
```

The `<local-data-folder>` should contain the following structure:

- some_case/image.tif
- another_case/img.tif
- etc.

Visit [http://localhost:8080/docs](http://localhost:8080/docs) to checkout the available endpoints. There is also a simple viewer, which can be accessed via [http://localhost:8080/validation_viewer](http://localhost:8080/validation_viewer).

## Overview

The _WSI Service_ enables users to stream Whole Slide Images (WSI) tile-based via HTTP. It is based on a FastAPI webserver and a number of plugins to access whole slide image data.

Regarding the slide's metadata, it provides the extent of the base level (original image, level=0), its pixel size in nm (level=0), general tile extent, the total count of levels and a list of levels with information about its extent, downsampling factor in relation to the base level. Furthermore, the channel depth is given along with a list of all available channels.

Regions of the WSI can be requested on any of the available levels. There is also a way to access tiles of a predefined size of each level (e.g. useful for a [viewer](wsi_service/api/root/viewer.html)). Furthermore, it is possible to get a thumbnail, label and macro image.

There are several endpoints made available by this service:

- `GET /v3/slides/{slide_id}/info` - Get slide info
- `GET /v3/slides/{slide_id}/download` - Download slide
- `GET /v3/slides/{slide_id}/region/level/{level}/start/{start_x}/{start_y}/size/{size_x}/{size_y}` - Get slide region
- `GET /v3/slides/{slide_id}/tile/level/{level}/tile/{tile_x}/{tile_y}` - Get slide tile
- `GET /v3/slides/{slide_id}/thumbnail/max_size/{max_x}/{max_y}` - Get slide thumbnail image
- `GET /v3/slides/{slide_id}/label/max_size/{max_x}/{max_y}` - Get slide label image
- `GET /v3/slides/{slide_id}/macro/max_size/{max_x}/{max_y}` - Get slide macro image

The last five endpoints all return image data. The image format and its quality (e.g. for jpeg) can be selected. Formats include jpeg, png, tiff, bmp, gif.

When tiff is specified as output format for the region and tile endpoint the raw data of the image is returned. This is paricularly important for images with abitrary image channels and channels with a higher color depth than 8bit (e.g. fluorescence images). The channel composition of the image can be obtained through the slide info endpoint, where the dedicated channels are listed along with its color, name and bitness. Multi-channel images can also be represented as RGB-images (mostly for displaying reasons in the viewer). Note that the mapping of all color channels to RGB values is currently restricted to the first three channels. Single channels (or multiple channels) can be retrieved through the optional parameter image_channels as an integer array referencing the channel IDs.

The region and the tile endpoint also offer the selection of a layer with the index z in a Z-Stack.

Get a detailed description of each endpoint by running the WSI Service (see _Getting started_ section) and accessing the included Swagger UI [http://localhost:8080/v3/docs](http://localhost:8080/v3/docs).

### Standalone version

The WSI Service relies on the [Storage Mapper Service](https://www.gitlab.com/empaia/services/storage-mapper-service) to get storage information for a certain slide id. If activated (see _Getting started_ section), the WSI Service will be run in standalone mode using a local mapper. This local mapper fulfills the function of the storage mapper service, the id mapper service and part of the clinical data service by creating case ids for folders found in the data folder and slide ids for images within these case folders. In the standalone mode there are few additional endpoints, which can be accessed:

- `GET /cases/` - Get cases
- `GET /cases/{case_id}/slides/` - Get available slides
- `GET /slides/{slide_id}` - Get slide
- `GET /slides/{slide_id}/storage` - Get slide storage information

Get a detailed description of each endpoint by running the WSI Service (see _Getting started_ section) and accessing the included Swagger UI [http://localhost:8080/docs](http://localhost:8080/docs).

### Supported formats

Different formats are supported by plugins for accessing image data. Five base plugins are included and support the following formats:

- [openslide](./wsi_service_base_plugins/openslide/)
  - 3DHISTECH (\*.mrxs)
  - HAMAMATSU (\*.ndpi)
  - LEICA (\*.scn)
  - VENTANA (\*.bif)
  - VSF (\*.vsf)

- [pil](./wsi_service_base_plugins/pil/)
  - JPEG (\*.jpeg, \*.jpg)
  - PNG (\*.png)

- [tifffile](./wsi_service_base_plugins/tifffile/)
  - OME-TIFF (\*.ome.tif, \*.ome.tif, \*.ome.tiff, \*.ome.tf2, \*.ome.tf8, \*.ome.btf)

- [tiffslide](./wsi_service_base_plugins/tiffslide/)
  - APERIO (\*.svs)
  - GENERIC TIF (\*.tif / \*.tiff)

- [wsidicom](./wsi_service_base_plugins/wsidicom/)
  - DICOM FOLDER

## Setup

_This section shows how to run and create the WSI Service after checking out this repository. Based on a docker compose file and environment variables, it shows how to properly set up the WSI Service for different deployment scenarios. If you just want to get a first impression of the WSI service, go to [Quickstart](#quickstart)._

WSI Service is a python module and has to be run via docker.

Make sure [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) are installed.

Set environment variables in your shell or in a `.env` file:

```bash
WS_CORS_ALLOW_CREDENTIALS=False
WS_CORS_ALLOW_ORIGINS=["*"]
WS_DEBUG=False
WS_DISABLE_OPENAPI=False
WS_MAPPER_ADDRESS=http://localhost:8080/slides/{slide_id}/storage
WS_LOCAL_MODE=True
WS_ENABLE_VIEWER_ROUTES=True
WS_INACTIVE_HISTO_IMAGE_TIMEOUT_SECONDS=600
WS_MAX_RETURNED_REGION_SIZE=25000000
WS_MAX_THUMBNAIL_SIZE=500

COMPOSE_RESTART=no
COMPOSE_NETWORK=default
COMPOSE_WS_PORT=8080
COMPOSE_DATA_DIR=/data
```

Short explanation of the parameters used:

- `WS_CORS_ALLOW_CREDENTIALS` when set to true, then browser credentials are enabled (note: WS_CORS_ALLOW_ORIGINS must
not contain "*" in that case)
- `WS_CORS_ALLOW_ORIGINS` allow cors for different origins
- `WS_DEBUG` enables debug logging level
- `WS_DISABLE_OPENAPI` disable swagger api documentation (/docs`)
- `WS_MAPPER_ADDRESS` storage mapper service address
- `WS_LOCAL_MODE` when set to true, wsi service is started in local mode
- `WS_ENABLE_VIEWER_ROUTES` when set to true, there are additional routes available for viewing images:
  - Simple Viewer `/slides/{slide_id/}/viewer`
  - Validation Viewer `/validation_viewer` (only local mode)
- `WS_INACTIVE_HISTO_IMAGE_TIMEOUT_SECONDS` set timeout for inactive histo images (default is 600 seconds)
- `WS_MAX_RETURNED_REGION_SIZE` set maximum image region size for service (channels x width x height; default is 4 x 5000 x 5000)
- `WS_MAX_THUMBNAIL_SIZE` set maximum thumbnail size that can be requested
- `COMPOSE_RESTART` set to `no`, `always` to configure restart settings
- `COMPOSE_NETWORK` set network used for wsi service
- `COMPOSE_WS_PORT` set external port for wsi service
- `COMPOSE_DATA_DIR` mounted volume to the image data (e.g. `/testdata/OpenSlide_adapted`)

Then run

```bash
docker-compose up --build
```

It is not recommened to run the python package outside the specified docker image due to issues with library dependencies on different platforms.

## Update OpenSlide version

The WSI-Service uses a customized version of OpenSlide to support the VSF-format.

If you want to update the version of OpenSlide some steps are needed:

1. Update OpenSlide: the source code can be found here: [https://github.com/EMPAIA/openslide](https://github.com/EMPAIA/openslide)
2. Build the updated OpenSlide version. See here for more information: [https://gitlab.com/empaia/integration/ci-openslide](https://gitlab.com/empaia/integration/ci-openslide)
3. Update the value of `OPENSLIDE_VERSION` in the `Dockerfile`. Use the same value (commit hash in GitHub) as in step **2.**

## Development

**Important:** Make sure you don't have a virtual environment inside the `wsi-service` root folder.

Not only in application, also in development it is recommended not to use the python package outside the specified developer docker image due to issues with library dependencies on different platforms. For developers who have not developed with a docker container before, this may be a bit unfamiliar at first, but the next steps should help to set it up step by step.

Run

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

### Run debugging

Open VS Code and ensure you have the extensions _Docker_ and _Remote - Containers_ installed.

Use the Docker extension to attach VS Code to the running `wsi-service` container (use `Attach Visual Studio Code` option).

A new VS Code window will open. After first start install the Python extension.

If not already open, open the folder `/wsi-service/`.

Go to the terminal windows of VS Code and activate the virtual environment created by poetry:

```bash
# use name of created venv

source /root/.cache/pypoetry/virtualenvs/wsi-service-<your_venv_suffix>/bin/activate
```

To stop and debug at any point in the code, use VS Code to start `Python: Remote Attach` while development composition is up and running.

### Run static code analysis and fix issues

Check your code by running the following statements before pushing changes:

```bash
isort .
black .
pycodestyle wsi_service wsi_service_base_plugins
pylint wsi_service wsi_service_base_plugins
```

### Run tests

Run in attached VS Code while development composition is up and running:

```bash
pytest --cov wsi_service --maxfail=1
```

To run tests locally, make sure you have the latest testdata (For access contact project maintainer).

After downloading the testdata, set the path of the `OpenSlide_adapted` folder as environment variable in your `.env` file:

```bash
COMPOSE_DATA_DIR=/testdata/OpenSlide_adapted
```

## Plugin development

Plugins are python packages following the naming scheme `wsi-service-plugin-PLUGINNAME` that need to implement a Slide class following the base class in [`slide.py`](wsi_service/slide.py). Additionally, there needs to be an `__init__.py` file like this:

```python
from .slide import Slide

def is_supported(filepath):
    return filepath.endswith(".tif")

async def open(filepath):
    return await Slide.create(filepath)
```

Once these minimal requirements are taken care of, the python package can be installed on top of an existing WSI Service docker image by simple running a Dockerfile along these lines:

```Dockerfile
FROM registry.gitlab.com/empaia/services/wsi-service

COPY wsi-service-plugin-PLUGINNAME.whl /tmp/wsi-service-plugin-PLUGINNAME.whl

RUN pip3 install /tmp/wsi-service-plugin-PLUGINNAME.whl
```

There are five base plugins ([openslide](./wsi_service_base_plugins/openslide/), [pil](./wsi_service_base_plugins/pil/), [tiffile](./wsi_service_base_plugins/tifffile/), [tiffslide](./wsi_service_base_plugins/tiffslide/), [wsidicom](./wsi_service_base_plugins/wsidicom/)) that can be used as templates for new plugins. Additionally to the mentioned minimal requirements these plugins use poetry to manage and create the python package. This is highly recommended when creating a plugin. Furthermore, these plugins implement tests based on pytest by defining a number of parameters on top of example integration test functions defined as part of the WSI Service ([plugin_example_tests](./wsi_service/tests/integration/plugin_example_tests)).

A more complete example of an external plugin integration can be found in the iSyntax integration repository ([wsi-service-plugin-isyntax](https://www.gitlab.com/empaia/services/wsi-service-plugin-isyntax)). That example includes the usage of an external service that is run in an additional docker container due to runtime limitations.
