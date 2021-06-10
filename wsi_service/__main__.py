import os
from distutils.util import strtobool

import uvicorn


def main():
    os.environ["data_dir"] = "/data"
    ws_default_port = 8080

    if os.environ["WS_DEFAULT_MAPPER_ADDRESS"] == "default":
        os.environ["local_mode"] = str(True)
        os.environ["mapper_address"] = f"http://localhost:{ws_default_port}/v1/slides/" + "{slide_id}/storage"
    else:
        os.environ["local_mode"] = str(False)
        os.environ["mapper_address"] = os.environ["WS_DEFAULT_MAPPER_ADDRESS"]

    uvicorn.run(
        "wsi_service.api:api",
        host="0.0.0.0",
        port=ws_default_port,
        reload=strtobool(os.environ["WS_DEBUG"]),
    )


if __name__ == "__main__":
    main()
