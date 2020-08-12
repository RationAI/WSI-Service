import math

import PIL
from werkzeug.exceptions import NotFound

import openslide


class Slide:
    def __init__(self, openslide_slide):
        self.openslide_slide = openslide_slide
        self.num_levels = self._calc_num_levels()

    def close(self):
        self.openslide_slide.close()

    def _calc_num_levels(self):
        min_extent = min(self.openslide_slide.dimensions)
        if min_extent >= 0:
            return int(math.log2(min_extent) + 1)
        else:
            return 0

    def get_info(self):
        info = {}
        # get slide extent
        info['extent'] = {'x': self.openslide_slide.dimensions[0], 'y': self.openslide_slide.dimensions[1]}
        # get num levels
        info['num_levels'] = self.num_levels
        # get slide resolution
        info['pixel_size_nm'] = int(round(1000 * float(self.openslide_slide.properties[openslide.PROPERTY_NAME_MPP_X])))
        # fake tile size, #TODO use openslide internal tile size if available
        info['tile_extent'] = {'x': 256, 'y': 256}
        return info

    #TODO: Optimize by caching high level
    def get_region(self, level, start_x, start_y, size_x, size_y):
        lvl0_location = start_x * (2**level), start_y * (2**level)
        base_level = self.openslide_slide.get_best_level_for_downsample(2**level + 0.1)
        remaining_downsample_factor = round((2**level) / self.openslide_slide.level_downsamples[base_level], 3)

        base_size = round(size_x * remaining_downsample_factor), round(size_y * remaining_downsample_factor)
        base_img = self.openslide_slide.read_region(lvl0_location, base_level, base_size)
        rgba_img = base_img.resize((size_x, size_y), resample=PIL.Image.BILINEAR, reducing_gap=1.0)
        return rgba_img.convert('RGB')

    def get_thumbnail(self, max_x, max_y):
        return self.openslide_slide.get_thumbnail((max_x, max_y))

    def get_label(self):
        if not 'label' in self.openslide_slide.associated_images:
            raise NotFound()
        label_rgba = self.openslide_slide.associated_images['label']
        return label_rgba.convert('RGB')
