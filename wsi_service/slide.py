class Slide:
    loader_name = ""

    def __init__(self, filepath, slide_id):
        raise (NotImplementedError)

    def close(self):
        raise (NotImplementedError)

    def get_info(self):
        raise (NotImplementedError)

    def get_region(self, level, start_x, start_y, size_x, size_y):
        raise (NotImplementedError)

    def get_thumbnail(self, max_x, max_y):
        raise (NotImplementedError)

    def _get_associated_image(self, associated_image_name):
        raise (NotImplementedError)

    def get_label(self):
        raise (NotImplementedError)

    def get_macro(self):
        raise (NotImplementedError)

    def get_tile(self, level, tile_x, tile_y):
        raise (NotImplementedError)
