# Standalone Gunicorn Image

To build, first provide `.env` file that configures the server. See examples in the repository root.
Then run:

> ``build.sh``
>
> ``source .env``
> 
> To test the deployment
> ``docker run -v $COMPOSE_DATA_DIR:/data -p $COMPOSE_WS_PORT:8080 --rm wsi-service-standalone:v0.0.1``
>
> To run detached (production)
> ``docker run -v $COMPOSE_DATA_DIR:/data -p $COMPOSE_WS_PORT:8080 -d wsi-service-standalone:v0.0.1``


