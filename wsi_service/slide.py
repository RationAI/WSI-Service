from werkzeug.exceptions import NotFound

import openslide


class Slide:
    def __init__(self, openslide_slide):
        self.openslide_slide = openslide_slide

    def close(self):
        self.openslide_slide.close()

    def get_info(self):
        info = {}
        # get slide extent
        info['extent'] = {'x': self.openslide_slide.dimensions[0], 'y': self.openslide_slide.dimensions[1]}
        # get num levels
        info['num_levels'] = self.openslide_slide.level_count
        # get slide resolution
        info['pixel_size_nm'] = int(round(1000 * float(self.openslide_slide.properties[openslide.PROPERTY_NAME_MPP_X])))
        # fake tile size, as openslide does not reveal real tile size
        info['tile_extent'] = {'x': 256, 'y': 256}
        info['level_dimensions'] = self.openslide_slide.level_dimensions

        return info

    # FIXME: use level coordinates, enable all pyramid levels
    def get_region(self, level, start_x, start_y, size_x, size_y):
        level_0_start_x = start_x# * (2**level)
        level_0_start_y = start_y# * (2**level)
        rgba_img = self.openslide_slide.read_region((level_0_start_x, level_0_start_y), level, (size_x, size_y))
        return rgba_img.convert('RGB')

    def get_thumbnail(self, max_x, max_y):
        return self.openslide_slide.get_thumbnail((max_x, max_y))

    def get_label(self):
        if not 'label' in self.openslide_slide.associated_images:
            raise NotFound()
        label_rgba = self.openslide_slide.associated_images['label']
        return label_rgba.convert('RGB')
