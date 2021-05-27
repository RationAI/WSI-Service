## Plugin to deform registered images

This plugin enables support for .sqreg files which contain deformation fields and links to the respective base images. Requested tiles are deformed on-the-fly using the existing plugins to load the original data. 

#### Binaries

This component requires platform specific binaries that can be obtained [in the EMPAIA Nextcloud](https://nextcloud.empaia.org/f/304275). They need to be placed next to the file `interpolate_c.py`. These binaries are  background IP of Fraunhofer MEVIS and may only used during and for the purpose of the EMPAIA project. They **must not be distributed** to third parties (see Section 5 of the "Kooperationsvertrag"). 

If does not work for you or with any other questions, please contact Johannes (johannes.lotz@mevis.fraunhofer.de).
#### Tests

`poetry run python -m pytest`

Tests currently need a running WSI-Service with the respective testing data (the file "CMU-1.tiff" from the OpenSlide testing data or any other  slide with slide_id `4b0ec5e0ec5e5e05ae9e500857314f20`).


