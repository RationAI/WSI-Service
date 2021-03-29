## Plugin to deform registered images

This plugin enables support for .sqreg files which contain deformation fields and links to the respective base images. Requested tiles are deformed on-the-fly using the existing plugins to load the original data. 

#### Tests

`poetry run python -m pytest`

Tests currently need a running WSI-Service with the respective testing data (the file "CMU-1.tiff" from the OpenSlide testing data or any other  slide with slide_id `4b0ec5e0ec5e5e05ae9e500857314f20`).

#### Important Note on Licensing

**IMPORTANT FOR EMPAIA:** This module contains background IP of Fraunhofer MEVIS which may be used **inside** the consortium during and for the performance of the project. It **may not be distributed** to third parties (see Section 5 of the "Kooperationsvertrag"). The python code will be licensed under MIT license.

If does not work for you or with any other questions, please contact Johannes (johannes.lotz@mevis.fraunhofer.de).