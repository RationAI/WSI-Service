import argparse
import os
import zipfile
from urllib.request import urlretrieve

import uvicorn


def set_env_from_args(data_dir, mapper_address, local_mode):
    os.environ["data_dir"] = data_dir
    os.environ["local_mode"] = str(local_mode)
    os.environ["mapper_address"] = mapper_address


def load_example_data(download_folder="/data"):
    if not os.path.exists(os.path.join(download_folder, "Aperio")):
        print("Beginning file download (13 GB)...")
        url = "https://nextcloud.empaia.org/s/4fpdFEn69gqgrgK/download"
        urlretrieve(url, os.path.join(download_folder, "..", "testdata.zip"))
        with zipfile.ZipFile(os.path.join(download_folder, "..", "testdata.zip"), "r") as zip_ref:
            zip_ref.extractall(os.path.join(download_folder, ".."))
        print("Done")


def main():
    default_port = 8080
    default_mapper_address = f"http://localhost:{default_port}/v1/slides/" + "{slide_id}/storage"
    parser = argparse.ArgumentParser(description="Webservice that serves histological whole-slide-images")
    parser.add_argument("data_dir", help="Base path to histo data")
    parser.add_argument("--port", default=default_port, help="Port the WSI-Service listens to")
    parser.add_argument("--debug", dest="debug", action="store_true", help="Use the debug config")
    parser.add_argument(
        "--load-example-data",
        dest="load_example_data",
        action="store_true",
        help="This will download an example image into the data folder before starting the server",
    )
    parser.add_argument(
        "--mapper-address",
        default=default_mapper_address,
        help="Mapper-Service Address",
    )
    args = parser.parse_args()

    if args.load_example_data:
        load_example_data()

    set_env_from_args(
        args.data_dir,
        args.mapper_address,
        args.mapper_address == default_mapper_address,
    )
    uvicorn.run("wsi_service.api:api", host="0.0.0.0", port=int(args.port), reload=args.debug)


if __name__ == "__main__":
    main()
