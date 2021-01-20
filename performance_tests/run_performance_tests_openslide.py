import os
import time

import openslide
import pandas as pd
from helpers import get_random_region_postions


def main():
    # settings
    slide_formats = ["Aperio", "Generic TIFF", "Hamamatsu", "MIRAX"]
    data_path = "/data/"
    slide_paths = {}
    slide_paths["Aperio"] = "Aperio/CMU-1.svs"
    slide_paths["Generic TIFF"] = "Generic TIFF/CMU-1.tiff"
    slide_paths["Hamamatsu"] = "Hamamatsu/OS-1.ndpi"
    slide_paths["MIRAX"] = "MIRAX/Mirax2.2-1.mrxs"
    region_sizes = [64, 128, 256, 512, 1024, 2048]
    number_of_samples = 256
    # run performance tests
    results = []
    for slide_format in slide_formats:
        print(slide_format)
        slide_id = slide_paths[slide_format]
        slide_file_extension = os.path.splitext(slide_id)[1][1:]
        openslide_slide = openslide.OpenSlide(os.path.join(data_path, slide_id))
        slide_info = {"extent": {"x": openslide_slide.dimensions[0], "y": openslide_slide.dimensions[1]}}
        # test region endpoint
        for region_size in region_sizes:
            print("region", region_size)
            random_region_positions = get_random_region_postions(slide_info["extent"], region_size, number_of_samples)
            pixels_per_region = region_size * region_size
            start_time = time.time()
            for start_x, start_y in random_region_positions:
                openslide_slide.read_region((start_x, start_y), 0, (region_size, region_size))
            elapsed_time = time.time() - start_time
            result = [
                slide_format,
                slide_file_extension,
                slide_id,
                "region",
                region_size,
                region_size,
                number_of_samples,
                elapsed_time,
            ]
            results.append(result)
        # save results
        df = pd.DataFrame(
            results,
            columns=[
                "slide_format",
                "slide_file_extension",
                "slide_filename",
                "endpoint",
                "size_x",
                "size_y",
                "number_of_samples",
                "elapsed_time",
            ],
        )
        df["pixels_per_tile"] = df["size_x"] * df["size_y"]
        df["pixels_per_second"] = (df["number_of_samples"] * df["pixels_per_tile"] / df["elapsed_time"]).astype(int)
        git_hash = os.environ["GIT_HASH"]
        os.makedirs(f"/scripts/results/results_{git_hash}/", exist_ok=True)
        df.to_csv(f"/scripts/results/results_{git_hash}/performance_tests_openslide.csv", index=False)


if __name__ == "__main__":
    main()
