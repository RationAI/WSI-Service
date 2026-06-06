# WSI Service

A general-purpose Whole Slide Image (WSI) server written in Python. Originally based on Empaia's WSI
Service, now maintained by RationAI with broader format support, pluggable auth, and pluggable data
discovery. It streams raster image tiles over HTTP — and, as of recently, also vector tiles
(MVT / PBF / GeoJSON / MBTiles) for annotation overlays.

> A prebuilt standalone Gunicorn image is published at
> [ghcr.io/RationAI/WSI-Service](https://github.com/RationAI/WSI-Service/pkgs/container/wsi-service).

## Contents

- [What it does](#what-it-does)
- [Quickstart](#quickstart)
- [Supported formats](#supported-formats)
- [Vector tile datasets (MVT / GeoJSON / MBTiles)](#vector-tile-datasets)
- [Configuration](#configuration)
- [Data mappers](#data-mappers)
- [Authentication](#authentication)
- [ICC profiles](#icc-profiles)
- [Plugin development](#plugin-development)
- [Development](#development)

## What it does

The WSI Service exposes Whole Slide Images over a FastAPI HTTP server. Clients can:

- Fetch slide metadata (extent at level 0, pixel size in nm, level pyramid, channel info).
- Request tiles or arbitrary regions at any pyramid level.
- Get thumbnails, label images, and macro images.
- Apply or download ICC profiles.
- Stream **vector tiles** for annotation overlays (MVT, PBF, GeoJSON, JSON, MBTiles).

Image endpoints (highlights — full set lives under `/v3/docs`):

| Endpoint | Purpose |
| --- | --- |
| `GET /v3/slides/info?slide_id=...` | Slide metadata |
| `GET /v3/slides/tile/level/{level}/tile/{x}/{y}?slide_id=...` | Tile at level |
| `GET /v3/slides/region/level/{level}/start/{x}/{y}/size/{w}/{h}?slide_id=...` | Arbitrary region |
| `GET /v3/slides/thumbnail/max_size/{x}/{y}?slide_id=...` | Thumbnail |
| `GET /v3/slides/label/max_size/{x}/{y}?slide_id=...` | Label image |
| `GET /v3/slides/macro/max_size/{x}/{y}?slide_id=...` | Macro image |
| `GET /v3/slides/icc_profile?slide_id=...` | ICC profile (gzipped bytes) |
| `GET /v3/slides/download?slide_id=...` | Raw slide download |

The `tile` and `region` endpoints accept an `image_format` parameter — raster formats
(`bmp`, `gif`, `jpeg`, `png`, `tiff`) are encoded by the server. Raw multi-channel TIFF is returned
when `image_format=tiff` and is the right choice for fluorescence or high-bit-depth data. Passthrough
formats (`raw`, `json`, `geojson`, `mvt`, `pbf`) return whatever the plugin produced unchanged — this
is how vector tiles are served (see below).

Full interactive documentation lives at `http://localhost:8080/v3/docs` once the service is running.

### Features at a glance

- **Auth, your way.** Plug in a JWT verifier, an LSAAI script, or disable auth entirely. Existing
  Keycloak/OAuth2 integration ships with the service.
- **Batch tile access.** Fetch many tiles per request instead of one HTTP round-trip per tile.
- **Custom local data mappers.** Decide for yourself how slide and case IDs are derived from your
  filesystem layout.
- **Direct file access.** Skip IDs — point at relative paths under the data root.
- **Vector tile streaming.** Serve precomputed MVT/GeoJSON/MBTiles tile sets alongside raster slides.

### Limitations

API versions prior to `v3` are not supported. The legacy Setup chapter has been replaced by a
[Quickstart](#quickstart). For production-style deployments, see `build_rationai` (cloud / load
balancer image) and `build_standalone` (Gunicorn image, Docker Compose friendly); each contains a
`build.sh`.

## Quickstart

The fastest path is the standalone Gunicorn image:

```bash
cd build_standalone
cp no-auth.env .env       # edit as needed
./build.sh
docker compose up
```

The service is then available at <http://localhost:8080/v3/docs>.

To run from sources via the dev compose:

```bash
docker compose up --build
```

Running outside Docker is **not recommended** — native dependencies (OpenSlide, libvips, etc.)
are pinned inside the image.

## Supported formats

Raster image formats are provided by base plugins. Each plugin can be enabled/disabled or
re-prioritized via `WS_PLUGIN_PRIORITY_<NAME>` env vars (see [Plugin development](#plugin-development)).

| Plugin | Formats |
| --- | --- |
| [openslide](./wsi_service_base_plugins/openslide/) | 3DHISTECH (`.mrxs`), HAMAMATSU (`.ndpi`), LEICA (`.scn`), VENTANA (`.bif`), ZEISS (`.czi`), DICOM folders |
| [pil](./wsi_service_base_plugins/pil/) | JPEG (`.jpeg`, `.jpg`), PNG (`.png`) |
| [tifffile](./wsi_service_base_plugins/tifffile/) | OME-TIFF (`.ome.tif`, `.ome.tiff`, `.ome.tf2`, `.ome.tf8`, `.ome.btf`) |
| [tiffslide](./wsi_service_base_plugins/tiffslide/) | APERIO (`.svs`), generic TIFF (`.tif`, `.tiff`) |
| [wsidicom](./wsi_service_base_plugins/wsidicom/) | DICOM folders |
| [mvt](./wsi_service_base_plugins/mvt/) | **Vector tiles** — see [next section](#vector-tile-datasets) |

## Vector tile datasets

The `mvt` plugin turns the WSI Service into a passthrough tile server for precomputed vector
datasets. Useful for streaming annotation layers, segmentation polygons, and other geo-style
overlays alongside histology slides.

### Vector datasets *are* slides

A vector dataset is **just another slide** to the server. It belongs to a case, gets a `slide_id`
from your mapper exactly like a raster slide, and is served through the **same `/v3/slides/...`
endpoints** — no separate API, no separate routing. Whether the underlying file is an `.svs` or a
`.mvt`/`.mbtiles`/manifest is a plugin-level detail.

In practice this means:

- The same `GET /v3/cases/slides?case_id=...` lists raster and vector slides side by side.
- `GET /v3/slides/info?slide_id=...` returns a `SlideInfo` (extent, level pyramid, tile size) for
  vector datasets too — channels are empty and `pixel_size_nm` is `-1`.
- `GET /v3/slides/tile/level/{level}/tile/{x}/{y}?slide_id=...` is the tile endpoint for **both**
  raster and vector — the format is selected per-request via `image_format`.
- Endpoints that don't make sense for vectors (`region`, `thumbnail`, `label`, `macro`) return
  `404`/`501` for vector slides, but the route itself is identical.

This is what lets a viewer mix raster histology and vector annotation overlays under one client
configuration: they're all just slides under the same case.

### What it accepts

The plugin opens whatever the mapper hands it as a slide source. That source can be:

- **A directory** in `z/x/y.ext` layout — zoom range discovered automatically.
- **A single tile file** — `.mvt`, `.pbf`, `.json`, `.geojson`, and their `.gz` variants. Served as
  the single tile at level 0, `(0, 0)`.
- **A manifest JSON file** that points at a sibling tile directory on disk (see [schema](#manifest-format)).
- **An MBTiles file** (`.mbtiles`) — SQLite-backed tile archive.

### Directory layout

```text
/dataset_root
  /0/0/0.mvt
  /1/0/0.mvt
  /1/0/1.mvt
  /1/1/0.mvt
  /1/1/1.mvt
  ...
```

The plugin scans available zoom directories and constructs the pyramid. WSI-Service level `0` maps
to the **highest available zoom** (most detailed), matching the convention of raster slides.

### Manifest format

A **manifest is a server-side file**, not an HTTP payload — there is no API endpoint to register or
upload one. You place a JSON file next to the tile directory on disk, and your mapper exposes that
file as a slide source. When the plugin opens it, it resolves `root` relative to the manifest's
parent directory and serves tiles from there.

Minimal example:

```json
{
  "root": "tiles",
  "tile_size": 256,
  "scheme": "xyz",
  "tile_suffixes": [".mvt.gz", ".mvt", ".pbf.gz", ".pbf", ".json.gz", ".json", ".geojson.gz", ".geojson"],
  "min_zoom": 0,
  "max_zoom": 14
}
```

Optional keys for finer control:

| Key | Meaning |
| --- | --- |
| `levels` | Explicit list of `{zoom, max_x, max_y}` or `{zoom, x_tiles, y_tiles}` entries. |
| `zoom_levels` | Whitelist of zoom levels to expose. |
| `bounds_by_zoom` | `{ "<zoom>": {"max_x": N, "max_y": N} }` per-level bounds. |
| `tile_suffix` | Single string, accepted as a shorthand for `tile_suffixes`. |

### Requesting vector tiles

Use the standard tile endpoint and pick a passthrough `image_format`:

```text
GET /v3/slides/tile/level/{level}/tile/{x}/{y}?slide_id=<id>&image_format=mvt
```

Supported `image_format` values for passthrough payloads: `raw`, `json`, `geojson`, `mvt`, `pbf`.
The server returns the bytes the plugin produced, with an appropriate `Content-Type`
(`application/vnd.mapbox-vector-tile` for `mvt`/`pbf`, `application/geo+json` for `geojson`, etc.).

### Notes & limitations

- **Region and thumbnail endpoints are not supported** for vector datasets — they return 501. The
  label and macro endpoints return 404. The vector plugin is tile-only by design.
- For files with **compound suffixes** like `.mvt.gz` or `.geojson.gz`, plugin auto-detection may
  only see the trailing `.gz`. If your dataset isn't picked up automatically, select the plugin
  explicitly with the `plugin=mvt` query parameter.
- Tiles stored gzipped on disk (or inside MBTiles) are **decompressed before being returned** — the
  upstream HTTP layer handles re-compression. Keeping payloads gzipped end-to-end is a possible
  future enhancement.
- MBTiles datasets use the **TMS** y-axis convention; the plugin transparently maps to/from XYZ on
  request.

## Configuration

Set environment variables in your shell or a `.env` file. The most common ones:

| Variable | Purpose |
| --- | --- |
| `WS_CORS_ALLOW_CREDENTIALS` | Enable browser credentials. `WS_CORS_ALLOW_ORIGINS` must not be `*` if true. |
| `WS_CORS_ALLOW_ORIGINS` | CORS origins, e.g. `["*"]`. |
| `WS_DEBUG` | Debug log level. |
| `WS_DISABLE_OPENAPI` | Hide Swagger UI at `/docs`. |
| `WS_MAPPER_ADDRESS` | External mapper URL (leave empty for local mode). |
| `WS_LOCAL_MODE` | `module.path:ClassName` of a local mapper (see [Data mappers](#data-mappers)). |
| `WS_ENABLE_LOCAL_ROUTES` | Expose local-mode endpoints. |
| `WS_ENABLE_VIEWER_ROUTES` | Expose `/slides/{id}/viewer` and `/validation_viewer`. |
| `WS_INACTIVE_HISTO_IMAGE_TIMEOUT_SECONDS` | Idle slide close timeout (default 600). |
| `WS_MAX_RETURNED_REGION_SIZE` | Max `channels × width × height` for `region` (default 4 × 5000 × 5000). |
| `WS_MAX_THUMBNAIL_SIZE` | Max thumbnail edge. |
| `WS_GET_TILE_APPLY_PADDING` | Pad `get_tile` like `get_region` when out-of-bounds. |
| `WS_PLUGIN_PRIORITY_<NAME>` | Override a plugin's priority. Negative disables it. |
| `COMPOSE_RESTART` | Compose `restart` policy. |
| `COMPOSE_NETWORK` | Docker network. |
| `COMPOSE_WS_PORT` | External port (default `8080`). |
| `COMPOSE_DATA_DIR` | Host data dir to mount (e.g. `/testdata/OpenSlide_adapted`). |

Auth- and mapper-specific variables are documented inline in the next two sections.

## Data mappers

A **mapper** is the component that decides what cases and slides exist and how their IDs are formed.
It's worth understanding how your chosen mapper builds slide and case IDs, since downstream auth and
URL conventions inherit from that.

Mapper-related endpoints:

- `GET /v3/cases/` — list cases
- `GET /v3/cases/slides?case_id={case}` — list slides in a case
- `GET /v3/slides?slide_id={slide}` — slide metadata
- `GET /v3/slides/storage?slide_id={slide}` — storage location

### External mapper (delegate to a remote service)

```bash
WS_MAPPER_ADDRESS=http://url.to.service/endpoint
WS_LOCAL_MODE=
WS_ENABLE_LOCAL_ROUTES=False
```

The remote endpoint must return a `SlideStorage` model.

### Local mappers

```bash
WS_MAPPER_ADDRESS=
WS_LOCAL_MODE=<module:Class>     # one of the built-in mappers below
WS_ENABLE_LOCAL_ROUTES=True
```

All local mappers implement `BaseMapper`:

- `get_cases(context=None)`
- `get_slides(case_id)`
- `get_slide(slide_id)`
- optional: `refresh()`, `load()` (context-independent mappers, for cache management)
- attribute `is_context_dependent` — whether `context` is required when listing cases.

Built-in mappers:

| Mapper | `WS_LOCAL_MODE` | Context-dependent? |
| --- | --- | --- |
| Simple | `wsi_service.simple_mapper:SimpleMapper` | No |
| Paths | `wsi_service.paths_mapper:PathsMapper` | Yes |
| CSV | `wsi_service.csv_mapper:CSVMapper` | No |
| Iterator | `wsi_service.mapper_iterator.iterator:IteratorMapper` | No |

#### Simple mapper

Builds the case → slide hierarchy from a two-level directory tree:

```text
data
├── case1
│   ├── slide1_1
│   └── slide1_2
├── case2
│   └── slide2_1
```

IDs are random UUID4s. Easy, but inflexible.

#### Paths mapper

Identifies cases and slides by their **relative path** to the data root. Requires a `context`
parameter (a relative directory) when listing cases. Useful for quick debugging.

#### CSV mapper

Reads a `.csv`/`.tsv` file (or directory of them) and constructs hierarchical IDs:

```bash
WS_LOCAL_MODE=wsi_service.csv_mapper:CSVMapper
CSWS_SOURCE='data.csv'      # file or directory
CSWS_SEPARATOR='\t'
CSWS_GROUP_1=0
CSWS_GROUP_2=1
CSWS_SLIDE_ID=2
CSWS_CASE_ID=3
CSWS_PATH=4
```

IDs come out as `group_1.group_2.w.slide_id` and `group_1.group_2.c.case_id`. Useful when you want
group-level access control without an external database.

#### Iterator mapper

Proof-of-concept directory walker with wildcard rules. Unfinished — contributions welcome.

## Authentication

Like mappers, auth is injected via an env var:

```bash
ENV_VAR=module.path.to.the.script:ClassName
```

Each integration defines its own additional env vars.

### OAuth2 / Keycloak example

```bash
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
```

Replace each `my_*` value with the value from your Keycloak deployment.

### Disabling authentication

```bash
WS_API_V3_INTEGRATION=wsi_service.api.v3.integrations.disable_auth:DisableAuth
```

A Life Science RI (LSAAI) integration is also available — see `env_auth` for example
configurations.

## ICC profiles

Profiles can be downloaded or applied server-side:

- `GET /v3/slides/icc_profile?slide_id=...` — gzipped profile bytes.
- Tile/region endpoints accept `icc_profile_intent`, one of `PERCEPTUAL`, `RELATIVE_COLORIMETRIC`,
  `SATURATION`, `ABSOLUTE_COLORIMETRIC`.
- `icc_profile_strict=true` enforces presence — the request fails with `412` if no profile is
  available, and with `500` if application was attempted and failed. With the default
  `icc_profile_strict=false`, requests succeed silently when no profile is present.

Profile application is best-effort and depends on the plugin's capabilities.

## Plugin development

A plugin is a Python package named `wsi-service-plugin-<NAME>` that:

1. Implements a `Slide` class extending the base in [`wsi_service/slide.py`](wsi_service/slide.py).
2. Exposes a minimal `__init__.py`:

   ```python
   from .slide import Slide

   priority = 10  # optional, default 0; higher wins; negative disables

   def is_supported(filepath):
       return filepath.endswith(".tif")

   async def open(filepath):
       return await Slide.create(filepath)
   ```

3. Optionally defines `start()` / `stop()` lifecycle callbacks (run on worker start/stop) and
   `supported_file_extensions` (a list of single-suffix strings used for auto-detection).

The `priority` value can be overridden at runtime with `WS_PLUGIN_PRIORITY_<NAME>=...`.

To register the plugin with the service image:

- Add it to the **base** `pyproject.toml`:

  ```toml
  wsi-service-plugin-<my-plugin-name> = { path = "wsi_service_base_plugins/<my-plugin-name>", develop = true }
  ```

- Update the relevant `Dockerfile`(s) to install any extra dependencies (e.g. a JRE for
  Bio-Formats).

Or install it on top of an existing image:

```Dockerfile
FROM wsi-service
COPY wsi-service-plugin-<name>.whl /tmp/
RUN pip3 install /tmp/wsi-service-plugin-<name>.whl
```

The five canonical base plugins (`openslide`, `pil`, `tifffile`, `tiffslide`, `wsidicom`) and the
newer `mvt` plugin are good references — they all use Poetry and share an integration-test pattern
based on parametrized pytest fixtures.

See [`wsi_service_base_plugins/README.md`](./wsi_service_base_plugins/README.md) for the integration
checklist.

## Development

> **Don't put a virtualenv inside `wsi-service/`.** It breaks Docker bind mounts.

Use the dev compose for an attached, live-reloading environment:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

### Debugging in VS Code

1. Install the **Docker** and **Remote - Containers** extensions.
2. Attach VS Code to the running `wsi-service` container (`Attach Visual Studio Code`).
3. Install the **Python** extension in the new window and open `/wsi-service/`.
4. Activate the Poetry venv in the integrated terminal:

   ```bash
   source /root/.cache/pypoetry/virtualenvs/wsi-service-<suffix>/bin/activate
   ```

5. Start `Python: Remote Attach` to set breakpoints.

### Static analysis

```bash
isort .
black .
pycodestyle wsi_service wsi_service_base_plugins
pylint wsi_service wsi_service_base_plugins
```

### Tests

```bash
pytest --cov wsi_service --maxfail=1
```

For full integration coverage you need the test dataset — contact the project maintainer for
access — and point `COMPOSE_DATA_DIR` at it:

```bash
COMPOSE_DATA_DIR=/testdata/OpenSlide_adapted
```

## OpenSlide version

A [fork](https://github.com/openslide/openslide/pull/605) of OpenSlide is currently bundled to
support ZEISS `.czi` images with JPEG XR compression. Once that PR lands upstream the build will
switch back to mainline OpenSlide. Historical note: an even older fork was used to support the
discontinued VSF format.

To upgrade OpenSlide, fetch a new source from
[openslide/openslide](https://github.com/openslide/openslide) and rebuild the image.

## The ecosystem

In the original Empaia setup, this service was one microservice among several. What's maintained
here is the **standalone** mode — a self-contained server whose behavior is shaped by Python classes
you inject via env vars in the form:

```text
ENV_VAR=module.path.to.the.script:ClassName
```

Each injected class brings its own set of env vars, which become active only when that class is in
use.
