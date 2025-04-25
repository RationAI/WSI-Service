# Changelog

## 0.13.5
- WSI_GET_TILE_APPLY_PADDING introduced.

## 0.13.4
- PIL plugin speed improvements

## 0.13.3
- Cleanup

## 0.13.2
- Changes in routes, now all slide/case data are query parameters.

## 0.13.1 
- Local Mode Cleanup: authentication, direct query.
- Update README on v13 changes.
- Support for Zeiss files `.czi`
- Openslide lib update
- Remove support for VSF files

## 0.13.0

- Slow Removal of Empaia-related workflows. 
- Removal of ``slide_id`` from path, as such IDs are then limited, and 
we are unable to reference slides by paths.

## 0.12.12

- Reverted wsidicom to 0.17.0

## 0.12.11

- Updated Dependencies

## 0.12.10

- Updated Dependencies

## 0.12.9

- Updated Dependencies

## 0.12.8

- Updated Dependencies

## 0.12.7

- Add .ndpi format to tiffslide

## 0.12.6

- Updated Dependencies

## 0.12.5

- Updated Dependencies

## 0.12.4

- Downgrade to Pillow < 10.0.0

## 0.12.3

- Updated Dependencies

## 0.12.2

- Updated Dependencies

## 0.12.1

- Updated Dependencies

## 0.12.0

- Updated to Pydantic v2
- Updated models to 0.4.3

## 0.11.16

- Updated Dependencies

## 0.11.15

- Updated Dependencies
- Added docker digest to Ubuntu 22.04

## 0.11.14

- Updated Dependencies

## 0.11.13

- Updated Dependencies

## 0.11.12

- Updated Dependencies

## 0.11.11

- Updated Dependencies

## 0.11.10

- Updated Dependencies

## 0.11.9

- Updated Dependencies

## 0.11.8

- Updated Dependencies
- Update base image to Ubuntu 22.04

## 0.11.7

- Updated Dependencies

## 0.11.6

- bugfix for plugin concept
- pinned wsidicom lib to 0.7.0

## 0.11.5

- bugfix for tifffiles plugin selection (ome.tif)

## 0.11.4

- Updated Dependencies

## 0.11.3

- Updated Dependencies

## 0.11.2

- Added possibility to disable plugins with priority < 0

## 0.11.1

- Missing huffman tables fix

## 0.11.0

- New plugin concept
- Extended slide info format content

## 0.10.20

- Updated Dependencies

## 0.10.19

- Updated Dependencies

## 0.10.18

- Updated Dependencies

## 0.10.17

- Updated Dependencies

## 0.10.16

- Updated Dependencies

## 0.10.15

- Updated Dependencies

## 0.10.14

- Updated Dependencies

## 0.10.13

- Updated Dependencies

## 0.10.12

- Fixed circular import error in plugins

## 0.10.11

- Updated Dependencies

## 0.10.10

- Adapted SyncSlide to include border handling and return numpy arrays as default

## 0.10.9

- Updated Dependencies

## 0.10.8

- Fixed direct tile access for YCbCr

## 0.10.7

- Fixed support for grayscale images

## 0.10.6

- Added python package release
- Added SyncSlide for direct slide access

## 0.10.5

- Updated Dependencies

## 0.10.4

- Updated Dependencies

## 0.10.3

- Updated Dependencies

## 0.10.2

- Updated Dependencies

## 0.10.1

- tiffslide and openslide compatibility fix

## 0.10.0

- added tiffslide plugin with raw tile support for svs and tiff
- added tests for out of image region and tile requests
- added out of image region and tile support to wsi service
- added z-stack parameter validation
- added possibility to add a plugin query
- added padding color query for tile requests
- added level validation for region and tile requests
- updated viewer to openlayers 7.1.0

## 0.9.7

- Updated Dependencies

## 0.9.6

- Updated Dependencies

## 0.9.5

- Updated Dependencies

## 0.9.4

- Updated Dependencies

## 0.9.3

- Updated Dependencies

## 0.9.2

- moved tests folder

## 0.9.1

- fixed default storage mapper address

## 0.9.0

- introduced new structure to support different api versions
- added api v3

## 0.8.3

- Fixed openslide plugin thumbnail bug

## 0.8.2

- Updated Dependencies

## 0.8.1

- Updated Dependencies

## 0.8.0

- Added download endpoint

## 0.7.30

- Updated Dependencies

## 0.7.29

- Updated Dependencies

## 0.7.28

- Updated Dependencies

## 0.7.27

- Updated Dependencies

## 0.7.26

- Updated Dependencies

## 0.7.25

- Updated Dependencies

## 0.7.24

- Updated Dependencies

## 0.7.23

- Updated Dependencies
- Added additional checks for pixel size of generic tiff

## 0.7.22

- Updated Dependencies

## 0.7.21

- Updated Dependencies

## 0.7.20

- Updated Dependencies

## 0.7.19

- Updated Dependencies

## 0.7.18

- Updated Dependencies

## 0.7.17

- Updated dependancies and fixed tifffile dep

## 0.7.16

- Updated Dependencies

## 0.7.15

- Custom OpenSlide version will be used in Docker build
- Added adjustments to openslide plugin for VSF support

## 0.7.14

- Updated Dependencies

## 0.7.13

- Added DICOM plugin based on wsidicom
- Set pycodestyle max-length to 120
  - Some needed formattings in code and comments

## 0.7.12

- Updated Dependencies

## 0.7.11

- Updated Dependencies

## 0.7.10

- Fixed dev mode

## 0.7.9

- Updated Dependencies

## 0.7.8

- Use more meaningful http error codes

## 0.7.7

- Updated Dependencies

## 0.7.6

- Fixed no proxy setting for ci

## 0.7.5

- Updated Dependencies

## 0.7.4

- Updated Dockerfile

## 0.7.3

- Updated Dockerfile

## 0.7.2

- Small CI update

## 0.7.1

- Improved docker build time

## 0.7.0

- Updated CI
- Added pycodestyle check
- Updated models
- Updated dependencies
  - tifffile plugin now returns slightly different thumbnails

## 0.6.8

- Fixed slide_id bug for isyntax

## 0.6.7

- added cors_allow_origins to settings again and made allow_credentials also configurable via cors_allow_credentials

## 0.6.6

- allow all origins, which is now possible because frontends do no more use client credentials (instead they explicitly use an authorization header)

## 0.6.5

- Fixed debug layer in viewer
- Fixed validation viewer padding

## 0.6.4

- Bugfix for slide cache, added close on removal

## 0.6.3

- Bugfix for tiff: removed JPEG compression

## 0.6.2

- Added cache for slide/image handles
- Fixed Leica rounding bug

## 0.6.1

- removed explicit logging timestamps

## 0.6.0

- Extended async to all slide plugin functions
- Added cache for storage mapper
- Fixed slow response due to StreamingResponse

## 0.5.7

- Fixed local mode uuid generation

## 0.5.6

- Use storage address to cache open slides (workaround)
- Added logger

## 0.5.5

- Return requested single channel tiles as grayscale images

## 0.5.4

- Added quickstart section to README
- Added default command to docker image
- Changed default settings to local mode with enabled viewer
- Updated models
- Removed performance tests

## 0.5.3

- Added a refresh-method that is called in supporting plugins

## 0.5.2

- plugin call is now async for compatibility with the deformation plugin

## 0.5.1

- Enabled local mapper to work with multiple workers
- Made all endpoints async

## 0.5.0

- Added PIL base plugin to support image formats like jpg, png

## 0.4.7

- Added service status model

## 0.4.6

- Added flag to activate viewer routes
- Improved error handling for storage mapper requests

## 0.4.5

- Added max_thumbnail_size setting for thumbnail endpoint
- Added locking to slide manager

## 0.4.4

- Updated outdated python packages

## 0.4.3

- Improved OpenAPI docs and README

## 0.4.2

- Added info about plugin versions to /alive endpoint
- Added info about plugin creation

## 0.4.1

- Automatically set fastapi version
- Fix for padding color in global settings

## 0.4.0

- Implemented plugins based on python packages
- Added base plugins openslide, tifffile

## 0.3.1

- Added pre-loading of files for the local mapper
- Added support for philips tiff-files

## 0.3.0

- Added max_x and max_y parameter to label and macro route to restrict image size
- Added padding_color in tile route to enable setting background color for slide tiles in viewer

## 0.2.4

- Populate settings from environment

## 0.2.3

- Refactored wsi-service (entrypoint, tests, color value in info, philips sdk)

## 0.2.2

- Fixed deformation bug in deformation_plugin
- Changed data format from png to jpeg in deformation_plugin

## 0.2.1

- Updated docker image from Python 3.8 to 3.9

## 0.2.0

- Added support for deformed slides in .sqreg format (requires additional (optional) binaries)

## 0.1.3

- Fix for unequal tile sizes in info route

## 0.1.2

- Added support for Philips isyntax format
- Restructured tests and test pipeline
- Starting service via docker-compose

## 0.1.1

- CI: Added version check
