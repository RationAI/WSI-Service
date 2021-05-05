import importlib
import sys
from io import BytesIO

import numpy as np
import pixelengine


class IsyntaxSlide:
    def __init__(self, filepath, slide_id):
        self.filepath = filepath
        self.slide_id = slide_id

        if importlib.find_loader("pixelengine") is None:
            self.result = {"rep": "error", "status_code": 422, "detail": f"Could not import Philips pixel engine."}

        try:
            render_backend, render_context = self.__get_backends("SOFTWARE")
            self.pixel_engine = pixelengine.PixelEngine(render_backend, render_context)
            self.pe_input = self.pixel_engine["in"]
            self.pe_input.open(filepath)

            self.image_names = []
            for index in range(self.pe_input.num_images):
                image_type = self.pe_input[index].image_type
                self.image_names.append(image_type)

            self.result = {"rep": "success", "status_code": 200, "detail": f""}
        except RuntimeError as ex:
            self.result = {"rep": "error", "status_code": 422, "detail": f"Failed to open isyntax file. [{ex}]"}

    def close(self):
        self.pe_input.close()

    def get_info(self):
        if "WSI" in self.image_names:
            return self.__get_slide_info(self.slide_id, "WSI")
        else:
            return {"rep": "error", "status_code": 422, "detail": f"File does not contain WSI data."}

    def get_region(self, level, start_x, start_y, size_x, size_y):
        image = self.pe_input["WSI"]
        slide_info = self.__get_slide_info(self.slide_id, "WSI")

        if len(slide_info["levels"]) <= level:
            return {
                "rep": "error",
                "status_code": 422,
                "detail": f"""The requested pyramid level is not available. 
                    The coarsest available level is {len(slide_info["levels"]) - 1}.""",
            }

        view_range = [
            start_x * (2 ** level),
            (start_x + size_x) * (2 ** level),
            start_y * (2 ** level),
            (start_y + size_y) * (2 ** level),
            level,
        ]

        try:
            # get data envelopes for requested levels
            data_envelopes = image.source_view.data_envelopes(level)
            regions = image.source_view.request_regions([view_range], data_envelopes, False, [254, 254, 254])
            # we only requested on region so we need to wait here until region is ready
            region = self.pixel_engine.wait_any()[0]
            pixel_buffer_size, patch_width, patch_height = self.__calculate_patch_size(image.source_view, region)
            pixels = np.empty(int(pixel_buffer_size), dtype=np.uint8)
            region.get(pixels)
            return {"rep": "success", "status_code": 200, "detail": f""}, pixels, patch_width, patch_height
        except RuntimeError as ex:
            return {"rep": "error", "status_code": 422, "detail": f"Philips SDK error [{ex}]"}, None, None, None

    def get_thumbnail(self, max_x, max_y):
        slide_info = self.__get_slide_info(self.slide_id, "WSI")
        thumb_level = len(slide_info["levels"]) - 1
        for i, level in enumerate(slide_info["levels"]):
            if level["extent"]["x"] < max_x or level["extent"]["y"] < max_y:
                thumb_level = i
                break
        level_extent_x = int(slide_info["levels"][thumb_level]["extent"]["x"])
        level_extent_y = int(slide_info["levels"][thumb_level]["extent"]["y"])

        if max_x > max_y:
            max_y = max_y * (level_extent_y / level_extent_x)
        else:
            max_x = max_x * (level_extent_x / level_extent_y)

        return self.get_region(thumb_level, 0, 0, level_extent_x, level_extent_y)

    def _get_associated_image(self, associated_image_name):
        if associated_image_name in self.image_names and self.pe_input[associated_image_name] is not None:
            pixel_data = self.pe_input[associated_image_name].image_data
            return pixel_data
        else:
            return {
                "rep": "error",
                "status_code": 422,
                "detail": f"Associated image {associated_image_name} does not exist.",
            }

    def get_label(self):
        return self._get_associated_image("LABELIMAGE")

    def get_macro(self):
        return self._get_associated_image("MACROIMAGE")

    def get_tile(self, level, tile_x, tile_y):
        slide_info = self.__get_slide_info(self.slide_id, "WSI")
        return self.get_region(
            level,
            tile_x * slide_info["tile_extent"]["x"],
            tile_y * slide_info["tile_extent"]["y"],
            slide_info["tile_extent"]["x"],
            slide_info["tile_extent"]["y"],
        )

    # private members

    def __get_slide_levels(self, image):
        derived_levels = self.pe_input[image].source_view.num_derived_levels
        levels = []
        for resolution in range(derived_levels):
            dim = self.pe_input[image].source_view.dimension_ranges(resolution)
            # we need to calculate level dimensions for x and y manually
            dim_x = (dim[0][2] - dim[0][0]) / dim[0][1]
            dim_y = (dim[1][2] - dim[1][0]) / dim[1][1]
            levels.append({"extent": {"x": dim_x, "y": dim_y, "z": 1}, "downsample_factor": (2 ** resolution)})

        return levels, derived_levels

    def __get_pixel_size(self, image):
        units = self.pe_input[image].source_view.dimension_units
        scale = self.pe_input[image].source_view.scale

        if units[0] == "MicroMeter":
            pixel_size_nm_x = scale[0] * 1000
            pixel_size_nm_y = scale[1] * 1000
        else:
            # other units supported?
            pixel_size_nm_x = scale[0]
            pixel_size_nm_y = scale[1]

        return [pixel_size_nm_x, pixel_size_nm_y, 0]

    def __get_slide_info(self, slide_id, image):
        levels, len_levels = self.__get_slide_levels(image)
        extent = self.pe_input[image].source_view.pixel_size
        tile_extent = self.pe_input[image].block_size(0)
        try:
            slide_info = {
                "id": slide_id,
                "channels": "rgb",
                "channel_depth": 8,
                "extent": {"x": extent[0], "y": extent[1], "z": 1},
                "pixel_size_nm": self.__get_pixel_size(image),
                "tile_extent": {"x": tile_extent[0], "y": tile_extent[1], "z": 1},
                "num_levels": len_levels,
                "levels": levels,
            }
            return slide_info
        except Exception as ex:
            return {"rep": "error", "status_code": 422, "detail": f"Failed to gather slide info from file [{ex}]."}

    def __get_backends(self, back_end):
        for b_end in backends:
            if b_end.name == back_end:
                return b_end.backend(), b_end.context()
        return None

    def __calculate_patch_size(self, view, region):
        x_start, x_end, y_start, y_end, level = region.range
        dim_ranges = view.dimension_ranges(level)
        patch_width, patch_height = self.__calc_patch_width_height(x_start, x_end, y_start, y_end, dim_ranges)
        pixel_buffer_size = patch_width * patch_height * 3
        return pixel_buffer_size, patch_width, patch_height

    def __calc_patch_width_height(self, x_start, x_end, y_start, y_end, dim_ranges):
        patch_width = int(1 + (x_end - x_start) / dim_ranges[0][1])
        patch_height = int(1 + (y_end - y_start) / dim_ranges[1][1])
        return patch_width, patch_height


# rendering backends
class Backend:
    def __init__(self, name, context, backend):
        self.name = name
        self.context = context[0]
        self.backend = backend[0]
        self.contextclass = context[1]
        self.backendclass = backend[1]


backends = [
    Backend(
        "SOFTWARE",
        ["softwarerendercontext", "SoftwareRenderContext"],
        ["softwarerenderbackend", "SoftwareRenderBackend"],
    ),
    Backend("GLES2", ["eglrendercontext", "EglRenderContext"], ["gles2renderbackend", "Gles2RenderBackend"]),
    Backend("GLES3", ["eglrendercontext", "EglRenderContext"], ["gles3renderbackend", "Gles3RenderBackend"]),
]

# import backend libs if supported
valid_backends = []
for backend in backends:
    try:
        if backend.context not in sys.modules:
            contextlib = __import__(backend.context)
        if backend.backend not in sys.modules:
            backendlib = __import__(backend.backend)
    except RuntimeError:
        pass
    else:
        backend.context = getattr(contextlib, backend.contextclass)
        backend.backend = getattr(backendlib, backend.backendclass)
        valid_backends.append(backend)
backends = valid_backends
