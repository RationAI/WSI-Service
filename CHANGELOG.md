# Changelog

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
