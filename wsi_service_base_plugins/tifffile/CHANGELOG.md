# Changelog

## 0.5.0

- Added generic multichannel TIFF support for non-OME `.tif`/`.tiff` files.
  - Page-per-channel (planar, channel-per-IFD) and chunky (`SamplesPerPixel > 1`, non-RGB photometric) layouts are now recognized.
  - Channel names are extracted from ImageJ metadata or Bio-Formats `ImageDescription` hints, falling back to `Channel N` with an R/G/B/CMY/W palette cycle.
  - Pixel size is derived from `XResolution`/`YResolution`/`ResolutionUnit` tags (with a 1 µm/px fallback).
  - Plain RGB(A) non-OME TIFFs are intentionally left to the `tiffslide` plugin.
  - TODO: Missing tests
- Plugin priority bumped to `2` so multichannel non-OME TIFFs route here ahead of `tiffslide`.

## 0.4.2

- Updated dependencies

## 0.4.1

- Updated dependencies

## 0.4.0

- Updated for new plugin concept

## 0.3.1

- Updated dependencies

## 0.3.0

- Removed parameter validation (already part of wsi service)

## 0.2.0

- Updated to v3 models

## 0.1.3

- Updated dependencies

## 0.1.2

- Updated dependencies

## 0.1.1

- Updated dependencies
