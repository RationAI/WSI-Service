# Changelog

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
