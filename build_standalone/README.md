# Standalone Gunicorn Image

To build, run the docker from root of the repository folder:

> ``build.sh``
> 
> ``export COMPOSE_DATA_DIR=/path/to/your/desired/data/root``
> 
> ``docker run -v $COMPOSE_DATA_DIR:/data -p <YOUR DESIRED PORT>:8080 wsi-service-standalone:v0.0.1``