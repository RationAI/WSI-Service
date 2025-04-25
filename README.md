# WSI Service

This is a general purpose WSI server written in Python. The server is based on Emapaia's WSI service. It supports
numerous WSI formats. The service is managed & features are added by RationAI.

### Features:

:key: Authentication. Pass a token, write a logics of verifying it and provide logics on which slide IDs are
allowed to view by whom. Or just parse tokens. Or just re-use existing implementation. Or simply disable auth.

:bus: Batch access. Do not fetch single tile per request. 

:black_nib: Custom local access address mappers. Add your own logics on how case and slide IDs are derived. 

:open_file_folder: Direct file access. We don't force you to use IDs: just select a file mapper and
access slides by their relative path to the server data root.


### Limitations:

API versions prior ``v3`` are not supported.

The Setup chapter in this README is outdated: we will try to provide simple quickstart and setup options if
there will be interest. For now, refer to ``build_rationai`` which builds a cloud-ready docker image
(meant for balance loaders). Or `build_standalone` which uses gunicorn to spin up standalone service (meant for docker compose).
Each folder contains ``build.sh`` file that automates image creation.

## Overview

The _WSI Service_ enables users to stream Whole Slide Images (WSI) tile-based via HTTP. It is based on a FastAPI webserver and a number of plugins to access whole slide image data.

Regarding the slide's metadata, it provides the extent of the base level (original image, level=0), its pixel size in nm (level=0), general tile extent, the total count of levels and a list of levels with information about its extent, downsampling factor in relation to the base level. Furthermore, the channel depth is given along with a list of all available channels.

Regions of the WSI can be requested on any of the available levels. There is also a way to access tiles of a predefined size of each level (e.g. useful for a [viewer](wsi_service/api/root/viewer.html)). Furthermore, it is possible to get a thumbnail, label and macro image.

There are several endpoints made available by this service:

- `GET /v3/slides/info?slide={slide_íd}` - Get slide info
- `GET /v3/slides/download?slide={slide_íd}` - Download slide
- `GET /v3/slides/region/level/{level}/start/{start_x}/{start_y}/size/{size_x}/{size_y}?slide={slide_íd}` - Get slide region
- `GET /v3/slides/tile/level/{level}/tile/{tile_x}/{tile_y}?slide={slide_íd}` - Get slide tile
- `GET /v3/slides/thumbnail/max_size/{max_x}/{max_y}?slide={slide_íd}` - Get slide thumbnail image
- `GET /v3/slides/label/max_size/{max_x}/{max_y}?slide={slide_íd}` - Get slide label image
- `GET /v3/slides/macro/max_size/{max_x}/{max_y}?slide={slide_íd}` - Get slide macro image

The last five endpoints all return image data. The image format and its quality (e.g. for jpeg) can be selected. Formats include jpeg, png, tiff, bmp, gif.

When tiff is specified as output format for the region and tile endpoint the raw data of the image is returned. This is paricularly important for images with abitrary image channels and channels with a higher color depth than 8bit (e.g. fluorescence images). The channel composition of the image can be obtained through the slide info endpoint, where the dedicated channels are listed along with its color, name and bitness. Multi-channel images can also be represented as RGB-images (mostly for displaying reasons in the viewer). Note that the mapping of all color channels to RGB values is currently restricted to the first three channels. Single channels (or multiple channels) can be retrieved through the optional parameter image_channels as an integer array referencing the channel IDs.

The region and the tile endpoint also offer the selection of a layer with the index z in a Z-Stack.

Get a detailed description of each endpoint by running the WSI Service (see _Getting started_ section) and accessing the included Swagger UI [http://localhost:8080/v3/docs](http://localhost:8080/v3/docs).

## The Ecosystem

In the original Empaia implementation, the WSI service interacted with other 
microservices. The service maintained here is the discontinued standalone
service mode. Its purpose is to provide versatile WSI access with configurable behavior.
This is achieved by injected python classes implementing given functionality.
The injection always defines

`````python
ENV_VAR=module.path.to.the.script:ClassName
`````

which will get instantiated. These classes usually also define their own set of
environmental variables which become recognized as soon as a particular injected
logics is used.

## Mappers

The WSI Service detects its data using mappers. A mapper fulfills the function of 
a data detector which defines what cases, slides are available and what is their relationship.

**Important is to learn how slide and case IDs are constructed based on the mapper logics**.


The server then offers these sets of endpoints that allow you querying the slide
and case relationship:

- `GET /v3/cases/` - Get cases
- `GET /v3/cases/slides?case_id={case}` - Get available slides
- `GET /v3/slides?slide_id={slide}` - Get slide
- `GET /v3/slides/storage?slide_id={slide}` - Get slide storage information

Get a detailed description of each endpoint by running the WSI Service (see _Getting started_ section) and accessing the included Swagger UI [http://localhost:8080/docs](http://localhost:8080/docs).

### External Data Mappers
If you want to configure custom mapper, it needs to return ``SlideStorage`` model. Then, you can configure
in the env:
`````bash
WS_MAPPER_ADDRESS=http://url.to.service/endpoint
WS_LOCAL_MODE=
WS_ENABLE_LOCAL_ROUTES=False
`````

### Local Data Mappers
Out of the box, local mappers are supported like so:
`````bash
WS_MAPPER_ADDRESS=
WS_LOCAL_MODE=<PYTHON MODULE PATH - SEE BELOW>
WS_ENABLE_LOCAL_ROUTES=True  # or False, but then local mode endpoints will not be available
`````
Following subsections describe all builtin local mappers:
#### Mapper: Simple Mapper
> ``WS_LOCAL_MODE=wsi_service.simple_mapper:SimpleMapper``

Simple mapper will create the case > slide hierarchy from your filesystem.
The files must be placed in two-level deep hierarchy: 
`````html
data
├── case1
│   ├── slide1_1
│   └── slide1_2
├── case2
│   └── slide2_1
...
`````
It's simple, but inflexible. IDs are generated randomly as UUID4.


#### Mapper: Paths Mapper
> ``WS_LOCAL_MODE=wsi_service.paths_mapper:PathsMapper``

The paths mapper does not yet support cases. You can access
any slide by its path relative to the server data directory root.

This mapper is manily for fast-use, debugging purposes. It is not matured enough.

#### Mapper: CSV Mapper
>  ````
>   WS_LOCAL_MODE=wsi_service.csv_mapper:CSVMapper
>   CSWS_SOURCE='data.csv'  # can be also a directory
>   CSWS_SEPARATOR='\t'
>   CSWS_GROUP_1=0
>   CSWS_GROUP_2=1
>   CSWS_SLIDE_ID=2
>   CSWS_CASE_ID=3
>   CSWS_PATH=4
> ````
> 

The CSV Mapper is more flexible option. It allows you to configure the
file or directory to scan for csv (scanned files are *.csv and *.tsv),
the separator character, and the order of columns. Above are shown ``CSWS_*``
default values - you don't have to define them if they are sufficient for your use.

The slide and case IDs are constructed then like this: ``group_1.group_2.w.slide_id``
and ``group_1.group_2.c.case_id``. This can come in handy when you want to implement
custom authorization logics and want to avoid explicit databases - where you can group
your data to collections and resolve access on these.


#### Mapper: Iterator Mapper
>  ````
>   WS_LOCAL_MODE=wsi_service.mapper_iterator.iterator:IteratorMapper
> ````

This is a proof-of-concept implementation of a directory-walking logics.
It allows you to scan a filesystem for supported files, and automatically
register these with the help of wildcard specifications that guite the
detection process. It is not documented yet as it is not finished.
If you want to have this feature matured, please feel free to contribute.


### Authentication

Similar to mappers, you can provide a custom authentication logics.
Sample env text files show you how to configure an OAuth2 (JWT-based)
authentication, and a Life Science RI (LSAAI) authorization scripts 
are also available. **Injected AAA logics also drives what ENV variables are
available / necessary to configure.**

Example OAuth2 authorization (no authentication) based on Keycloak:
````bash
WS_API_V3_INTEGRATION=wsi_service.api.v3.integrations.empaia:EmpaiaApiIntegration
WS_IDP_URL=http://domain.url:port/auth/realms/MY_REALM
WS_CLIENT_ID=my_client
WS_CLIENT_SECRET=my_client_secret
WS_ORGANIZATION_ID=my_organization
WS_AUDIENCE=my_audience
WS_OPENAPI_TOKEN_URL=http://domain.url:port/auth/realms/MY_REALM/protocol/openid-connect/token
WS_OPENAPI_AUTH_URL=http://domain.url:port/auth/realms/MY_REALM/protocol/openid-connect/auth
WS_REWRITE_URL_IN_WELLKNOWN=http://domain.url:port/auth/realms/MY_REALM
WS_REFRESH_INTERVAL=300
````
Where you have to replace all ``my_*`` values with actual values from your Keycloak deployment, which lives
on `domain.url:port`.

Example setup without authentication:
`````bash
WS_API_V3_INTEGRATION=wsi_service.api.v3.integrations.disable_auth:DisableAuth
`````

## Supported formats

Different formats are supported by plugins for accessing image data. Five base plugins are included and support the following formats:

- [openslide](./wsi_service_base_plugins/openslide/)
  - 3DHISTECH (\*.mrxs)
  - HAMAMATSU (\*.ndpi)
  - LEICA (\*.scn)
  - VENTANA (\*.bif)
  - ZEISS (\*.czi)

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
WS_MAPPER_ADDRESS=http://localhost:8080/slides/storage?slide={slide_id}
WS_LOCAL_MODE=wsi_service.simple_mapper:SimpleMapper
WS_ENABLE_VIEWER_ROUTES=True
WS_INACTIVE_HISTO_IMAGE_TIMEOUT_SECONDS=600
WS_MAX_RETURNED_REGION_SIZE=25000000
WS_MAX_THUMBNAIL_SIZE=500
# get_region endpoint is padded by a color if no data avaialble, turn on also for get_tile if desired
WSI_GET_TILE_APPLY_PADDING=False

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

## OpenSlide version

A [fork](https://github.com/openslide/openslide/pull/605) of original openslide library is currently used to support ZEISS `.czi` images with JPEG XR compression. Once this feature is merged to
[openslide](https://github.com/openslide/openslide) the source of openslide library will be updated.

The WSI-Service originally used a customized version of [OpenSlide](https://github.com/EMPAIA/openslide) to support the VSF-format...


If you want to update the version of OpenSlide some steps are needed:

1. Update OpenSlide: the source code can be found here: [https://github.com/openslide/openslide](https://github.com/openslide/openslide)
2. Build the updated OpenSlide version.

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

priority = 10

def is_supported(filepath):
    return filepath.endswith(".tif")

async def open(filepath):
    return await Slide.create(filepath)
```

The `priority` value is optional and is `0` by default. If it is set, a higher value means that a plugin is preferred. The priority can also be overridden by an environment variable, e.g. by setting `WS_PLUGIN_PRIORITY_PLUGINNAME=10`. If the priority is set to a negative value, the plugin will be disabled.

Once these minimal requirements are taken care of, the python package can be installed on top of an existing WSI Service docker image by simple running a Dockerfile along these lines:

```Dockerfile
FROM wsi-service

COPY wsi-service-plugin-PLUGINNAME.whl /tmp/wsi-service-plugin-PLUGINNAME.whl

RUN pip3 install /tmp/wsi-service-plugin-PLUGINNAME.whl
```

There are six base plugins that can be used as templates for new plugins. Additionally to the mentioned minimal requirements these plugins use poetry to manage and create the python package. This is highly recommended when creating a plugin. Furthermore, these plugins implement tests based on pytest by defining a number of parameters on top of example integration test functions defined as part of the WSI Service).
