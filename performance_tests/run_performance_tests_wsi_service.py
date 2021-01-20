import os
import time

import pandas as pd
from helpers import get_random_region_postions, get_random_tiles
from joblib import Parallel, delayed

from wsi_service import WSIService


def main():
    # settings
    format_whitelist = ["Aperio", "Generic TIFF", "Hamamatsu", "MIRAX"]
    image_formats = ["jpeg", "png", "tiff"]
    region_sizes = [64, 128, 256, 512, 1024]
    parallel_requests_list = [1, 2, 4, 8, 16]
    number_of_samples = 256
    web_concurrency = os.environ["WEB_CONCURRENCY"]
    wsi_service_address = os.environ["WSI_SERVICE_ADDRESS"]
    # setup wsi service and get cases
    wsi_service = WSIService(host=wsi_service_address)
    cases = wsi_service.get_cases()
    results = []
    # run performance tests
    for case in cases:
        if len(case["slides"]) > 0:
            slide_format = case["local_case_id"]
            if slide_format in format_whitelist:
                print(slide_format)
                slide_id = case["slides"][0]
                slide_file_extension = os.path.splitext(wsi_service.get_slide(slide_id)["local_slide_id"])[1][1:]
                slide_info = wsi_service.get_info(slide_id)
                # test tile endpoint
                random_tiles = get_random_tiles(slide_info, number_of_samples)
                print("tile", slide_info["tile_extent"]["x"])
                for image_format in image_formats:
                    print(image_format)
                    for parallel_requests in parallel_requests_list:
                        start_time = time.time()
                        size_bytes = Parallel(n_jobs=parallel_requests)(
                            delayed(wsi_service.get_tile)(
                                slide_id, 0, tile_x, tile_y, params={"image_format": image_format}
                            )
                            for tile_x, tile_y in random_tiles
                        )
                        size_bytes = sum(size_bytes)
                        elapsed_time = time.time() - start_time
                        result = [
                            slide_format,
                            slide_file_extension,
                            wsi_service.get_slide(slide_id)["local_slide_id"],
                            "tile",
                            slide_info["tile_extent"]["x"],
                            slide_info["tile_extent"]["y"],
                            image_format,
                            number_of_samples,
                            parallel_requests,
                            web_concurrency,
                            size_bytes,
                            elapsed_time,
                        ]
                        results.append(result)
                # test region endpoint
                for region_size in region_sizes:
                    print("region", region_size)
                    random_region_positions = get_random_region_postions(
                        slide_info["extent"], region_size, number_of_samples
                    )
                    pixels_per_region = region_size * region_size
                    for image_format in image_formats:
                        print(image_format)
                        for parallel_requests in parallel_requests_list:
                            start_time = time.time()
                            size_bytes = Parallel(n_jobs=parallel_requests)(
                                delayed(wsi_service.get_region)(
                                    slide_id,
                                    0,
                                    start_x,
                                    start_y,
                                    region_size,
                                    region_size,
                                    params={"image_format": image_format},
                                )
                                for start_x, start_y in random_region_positions
                            )
                            size_bytes = sum(size_bytes)
                            elapsed_time = time.time() - start_time
                            result = [
                                slide_format,
                                slide_file_extension,
                                wsi_service.get_slide(slide_id)["local_slide_id"],
                                "region",
                                region_size,
                                region_size,
                                image_format,
                                number_of_samples,
                                parallel_requests,
                                web_concurrency,
                                size_bytes,
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
                "output_format",
                "number_of_samples",
                "parallel_requests",
                "web_concurrency",
                "size_bytes",
                "elapsed_time",
            ],
        )
        df["pixels_per_tile"] = df["size_x"] * df["size_y"]
        df["pixels_per_second"] = (df["number_of_samples"] * df["pixels_per_tile"] / df["elapsed_time"]).astype(int)
        df["kbit_per_second"] = (df["size_bytes"] / df["elapsed_time"] / 1000 * 8).astype(int)
        git_hash = os.environ["GIT_HASH"]
        os.makedirs(f"/scripts/results/results_{git_hash}/", exist_ok=True)
        df.to_csv(f"/scripts/results/results_{git_hash}/performance_tests_wsi_service.csv", index=False)


if __name__ == "__main__":
    main()
