# wsi-service-plugin-mvt

WSI-Service plugin for serving passthrough vector and JSON tile datasets.

## Supported inputs

- Directory trees in `z/x/y.ext` layout
- Single tile files: `.mvt`, `.pbf`, `.json`, `.geojson`, and gzipped variants
- Manifest JSON files pointing at a directory dataset
- `.mbtiles` files

## Directory layout

```text
/root
  /0/0/0.mvt
  /1/0/0.mvt
  /1/0/1.mvt
  /1/1/0.mvt
  /1/1/1.mvt
```

## Manifest example

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

`levels`, `zoom_levels`, and `bounds_by_zoom` are also supported for finer control.

## Notes

- WSI-Service tile level `0` maps to the highest available zoom.
- For `.mvt.gz`, `.pbf.gz`, `.json.gz`, and `.geojson.gz`, plugin auto-detection may depend on how your WSI-Service loader matches extensions. If it only checks the last suffix, select the plugin explicitly with `plugin=mvt`.
- Region and thumbnail endpoints are intentionally unsupported for vector-tile datasets.
