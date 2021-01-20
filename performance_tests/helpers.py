import random

random.seed(42)


def get_random_tiles(slide_info, number_of_samples):
    max_tile_x = int(slide_info["extent"]["x"] / slide_info["tile_extent"]["x"])
    max_tile_y = int(slide_info["extent"]["y"] / slide_info["tile_extent"]["y"])
    tiles = []
    for i in range(number_of_samples):
        tiles.append((random.randint(0, max_tile_x), random.randint(0, max_tile_x)))
    return tiles


def get_random_region_postions(base_extent, region_size, number_of_samples):
    region_positions = []
    for i in range(number_of_samples):
        region_positions.append(
            (random.randint(0, base_extent["x"] - region_size), random.randint(0, base_extent["y"] - region_size))
        )
    return region_positions
