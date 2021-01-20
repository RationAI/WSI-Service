import sys

import pandas as pd


def get_results(results_folder):
    results = pd.read_csv(f"{results_folder}/performance_tests_wsi_service.csv")
    return results[results["endpoint"] == "region"]


def get_pixels_per_second(results, slide_format, region_size, output_format, parallel_requests):
    result = results[
        (results["slide_format"] == slide_format)
        & (results["size_x"] == region_size)
        & (results["output_format"] == output_format)
        & (results["parallel_requests"] == parallel_requests)
    ]
    return float(result["pixels_per_second"])


def main():
    print(sys.argv[1], sys.argv[2])
    results_1 = get_results(sys.argv[1])
    results_2 = get_results(sys.argv[2])
    change_factor_sum = 0.0
    count = 0
    for slide_format in results_1["slide_format"].unique():
        for region_size in results_1["size_x"].unique():
            for output_format in results_1["output_format"].unique():
                for parallel_requests in results_1["parallel_requests"].unique():
                    result_1_pixels_per_second = get_pixels_per_second(
                        results_1, slide_format, region_size, output_format, parallel_requests
                    )
                    result_2_pixels_per_second = get_pixels_per_second(
                        results_2, slide_format, region_size, output_format, parallel_requests
                    )
                    change_factor = result_1_pixels_per_second / result_2_pixels_per_second
                    change_factor_sum += change_factor
                    change_factor = round(change_factor, 2)
                    print(
                        f"{slide_format:<15} {region_size:>4} {output_format:<4} {parallel_requests:>2} {change_factor:>8}"
                    )
                    change_factor_sum += change_factor
                    count += 1
    overall_change_factor = round(change_factor_sum / count, 2)
    print(f"Overall factor {overall_change_factor}")


if __name__ == "__main__":
    main()
