# Performance tests

## Overview

The scripts in this folder help measure the performance of the WSI service. Performance measurements include

- pixels/s
- kbit/s

and are currently measured for the following formats

- Aperio
- Generic TIFF
- Hamamatsu
- MIRAX

the following output image formats

- jpeg
- png
- tiff

the following area sizes

- 64
- 128
- 256
- 512
- 1024

and finally for a varying number of parallel requests up to 16.

## Run

After customizing the datapath in `run.sh`, this script can be used to start the performance tests. This will start the WSI service in Docker and then run the tests in another Docker requesting regions/tiles from the WSI service. Another important parameter can be set in `run.sh`, it is called `WEB_CONCURRENCY` and defines the number of workers for the WSI service. Running this script should create two csv files in `results/results_GITHASH`.

You can then create a series of plots for all the results using

```
python3 run_create_plots.py
```
![plot_example_performance_Generic%20TIFF_jpeg.png](plot_example_performance_Generic%20TIFF_jpeg.png)
*Note: Example of one of the plots for Generic TIFF. The selected output format was jpeg. A different number of parallel reuqest (1) to (16) was used to get the image regions. The OpenSlide baseline only shows the performance of the loading part. Check further remarks for details on this comparison.*

or compare the results of different runs, using e.g.

```
python3 run_results_comparison.py results/results_095c76f results/results_6112625
```

## Further remarks

- **results_6112625** measures the initial state before any performance optimizations.
- Although we have included some results in this repository for documentation purposes, they cannot really be used for comparison by others as the hardware setup may not be comparable.
- `run_performance_tests_openslide.py` does not use the WSI Service but directly makes use of OpenSlide to sequentially open different image regions. This is used for comparison with the WSI Service. Just keep in mind, that this is not a fair comparison. Direct OpenSlide is just setup for sequential loading. On the other side, it only opens the image and it is done. For the WSI Service this is only the first step, it additionally encodes the image again (e.g. jpeg, png, tiff), transfers it to the client and finally decodes the image.
