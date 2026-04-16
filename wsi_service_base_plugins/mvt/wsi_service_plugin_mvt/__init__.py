from wsi_service_plugin_mvt.slide import Slide

# Keep this list single-suffix friendly for plugin discovery systems that only check Path.suffix.
# Compound suffixes like .mvt.gz or .json.gz can still be opened by explicitly selecting plugin=mvt.
supported_file_extensions = [".json", ".geojson", ".mvt", ".pbf", ".mbtiles"]


async def open(filepath):
    return await Slide.create(filepath)
