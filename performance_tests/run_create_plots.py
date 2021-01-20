from glob import glob

import matplotlib.pyplot as plt
import pandas as pd


def create_performance_plot_sequential_openslide(results_folder):
    results_base = pd.read_csv(f"{results_folder}/performance_tests_openslide.csv")
    plt.figure(figsize=(10, 6))
    for slide_format in results_base["slide_format"].unique():
        results_format = results_base[results_base["slide_format"] == slide_format]
        plt.plot(results_format["size_x"].to_list(), results_format["pixels_per_second"].to_list(), label=slide_format)
        plt.yscale("log")
        plt.xticks(results_format["size_x"].to_list())
        plt.ylabel("pixels/second")
        plt.xlabel("region size")
    plt.legend(loc="lower right")
    plt.ylim([100000, 100000000])
    plt.title("Sequential loading of 256 random regions")
    plt.savefig(f"{results_folder}/sequential_openslide.png")


def create_performance_plot(results_folder):
    results = pd.read_csv(f"{results_folder}/performance_tests_wsi_service.csv")
    results_base = pd.read_csv(f"{results_folder}/performance_tests_openslide.csv")
    results = results[results["endpoint"] == "region"]
    for slide_format in results["slide_format"].unique():
        for output_format in results["output_format"].unique():
            plt.figure(figsize=(10, 6))
            results_format_base = results_base[results_base["slide_format"] == slide_format]
            results_format_base = results_format_base[results_format_base["size_x"] <= 1024]
            plt.plot(
                results_format_base["size_x"].to_list(),
                results_format_base["pixels_per_second"].to_list(),
                "k",
                label="OpenSlide",
            )
            for parallel_requests in results["parallel_requests"].unique():
                results_format = results[results["slide_format"] == slide_format]
                results_format = results_format[results_format["output_format"] == output_format]
                results_format = results_format[results_format["parallel_requests"] == parallel_requests]
                plt.plot(
                    results_format["size_x"].to_list(),
                    results_format["pixels_per_second"].to_list(),
                    label=f"WSI Service ({parallel_requests})",
                )
                plt.yscale("log")
                plt.xticks(results_format["size_x"].to_list())
                plt.ylabel("pixels/second")
                plt.xlabel("region size")
            plt.legend(loc="lower right")
            plt.ylim([100000, 100000000])
            plt.title(f"Loading, encoding, transfering and decoding of 256 random regions ({output_format})")
            plt.savefig(f"{results_folder}/performance_{slide_format}_{output_format}.png")


def main():
    for result_folder in glob("results/results_*"):
        print(result_folder)
        create_performance_plot_sequential_openslide(result_folder)
        create_performance_plot(result_folder)


if __name__ == "__main__":
    main()
