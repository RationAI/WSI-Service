# WSI Service

## Overview

The _WSI Service_ enables users to stream Whole Slide Images (WSI) tile-based via HTTP. It is based on a FastAPI webserver and OpenSlide to access whole slide image data.

Regarding the slide's metadata, it provides the extent of the base level (original image, level=0), its pixel size in nm (level=0), general tile extent, the total count of levels and a list of levels with information about its extent, downsampling factor in relation to the base level.

<img src="https://upload.wikimedia.org/wikipedia/commons/thumb/4/43/Image_pyramid.svg/1024px-Image_pyramid.svg.png" alt="CC BY-SA 3.0" width="200"/>

Regions of the WSI can be requested on any of the available levels. There is also a way to access tiles of a predefined size of each level (e.g. useful for a [viewer](wsi_service/viewer.html)). Furthermore, it is possible to get a thumbnail, label and macro image.

There are several endpoints made available by this service:

- `GET /v1/slides/{slide_id}/info` - Get slide info, e.g.

```json
{
  "id": "f863c2ef155654b1af0387acc7ebdb60",
  "channels": [
    {
      "id": 0,
      "name": "Red",
      "color": {
        "r": 255,
        "g": 126,
        "b": 0,
        "a": 0
      }
    },
    {
      "id": 1,
      "name": "Green",
      "color": {
        "r": 0,
        "g": 255,
        "b": 0,
        "a": 0
      }
    },
    {
      "id": 2,
      "name": "Blue",
      "color": {
        "r": 0,
        "g": 0,
        "b": 255,
        "a": 0
      }
    }
  ],
  "channel_depth": 8,
  "extent": {
    "x": 46000,
    "y": 32914,
    "z": 1
  },
  "num_levels": 7,
  "pixel_size_nm": {
    "x": 499,
    "y": 499,
    "z": null
  },
  "tile_extent": {
    "x": 256,
    "y": 256,
    "z": 1
  },
  "levels": [
    {
      "extent": {
        "x": 46000,
        "y": 32914,
        "z": 1
      },
      "downsample_factor": 1,
    },
    {
      "extent": {
        "x": 23000,
        "y": 16457,
        "z": 1
      },
      "downsample_factor": 2,
    },
```

[...]

```json
    {
      "extent": {
        "x": 1,
        "y": 1,
        "z": 1
      },
      "downsample_factor": 32768,
    }
  ]
}
```

- `GET /v1/slides/{slide_id}/region/level/{level}/start/{start_x}/{start_y}/size/{size_x}/{size_y}?image_format=jpeg&image_quality=90&image_channels=0&z=0` - Get slide region: Get region of the slide. Level 0 is highest (original) resolution. The available levels depend on the image. Coordinates are given with respect to the requested level.
- `GET /v1/slides/{slide_id}/tile/level/{level}/tile/{tile_x}/{tile_y}?image_format=jpeg&image_quality=90&z=0` - Get slide tile: Get tile of the slide. Extent of the tile is given in slide metadata. Level 0 is highest (original) resolution. The available levels depend on the image. Coordinates are given with respect to tiles, i.e. tile coordinate n is the n-th tile in the respective dimension. The tile route has an additional parameter `padding_color`, which takes care that parts of the tile, that are outside the image extent are filled with a given color. The padding color expects a 24bit Hex-string which is `#FFFFFF` (white) by default.
- `GET /v1/slides/{slide_id}/thumbnail/max_size/{max_x}/{max_y}?image_format=jpeg&image_quality=90` - Get slide thumbnail image
- `GET /v1/slides/{slide_id}/label/max_size/{max_x}/{max_y}?image_format=jpeg&image_quality=90` - Get slide label image
- `GET /v1/slides/{slide_id}/macro/max_size/{max_x}/{max_y}?image_format=jpeg&image_quality=90` - Get slide macro image

The last five endpoints all return image data. The image format and its quality (e.g. for jpeg) can be selected. Formats include jpeg, png, tiff, bmp, gif. When tiff is specified as output format the raw data of the image is returned. This is paricularly important for images with abitrary image channels and channels with a higher color depth than 8bit (e.g. fluorescence images). The channel composition of the image can be obtained through the slide info endpoint, where the dedicated channels are listed along with its color, name and bitness. Multi-channel images can also be represented as RGB-images (mostly for displaying reasons in the viewer). Note that the mapping of all color channels to RGB values is currently restricted to the first three channels. Single channels (or multiple channels) can be retrieved through the optional parameter `image_channels` as an integer array referencing the channel IDs.

The region and the tile endpoint also offer the selection of a layer with the index z in a Z-Stack.

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


### Standalone version

The WSI Service relies on the [Storage Mapper Service](https://gitlab.cc-asp.fraunhofer.de/empaia/platform/data/storage-mapper-service) to get storage information for a certain slide*id. If the mapper-address is not provived (see \_How to run*), the WSI Service will be run in standalone mode using a local mapper. This local mapper fulfills the function of the storage mapper service, the id mapper service and part of the clinical data service by creating case ids for folders found in the data folder and slide ids for images within these case folders. In the standalone mode there are few additional endpoints, which can be accessed:

- `GET /v1/cases/` - Get cases
- `GET /v1/cases/{case_id}/slides/` - Get available slides
- `GET /v1/slides/{slide_id}` - Get slide
- `GET /v1/slides/{slide_id}/storage` - Get slide storage information

There is a validation viewer, which can be used by accessing: http://localhost:8080/v1/validation_viewer

There is also a simple viewer, which can be used by accessing: http://localhost:8080/v1/slides/{slide_id}/viewer

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
