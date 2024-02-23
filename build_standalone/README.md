# Standalone Gunicorn Image

To build, run the docker from root of the repository folder:

> docker build -t emapia-wsi-service:v1 -f Dockerfile ../
> export COMPOSE_DATA_DIR=/mnt/rbd/data/sftp
> docker run -v $COMPOSE_DATA_DIR:/data -p <YOUR DESIRED PORT>:8080 emapia-wsi-service:v1