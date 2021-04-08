import argparse
import os
import shutil
import zipfile
from urllib.request import urlretrieve

import uvicorn


def set_env_from_args(data_dir, mapper_address, local_mode):
    os.environ["data_dir"] = data_dir
    os.environ["local_mode"] = str(local_mode)
    os.environ["mapper_address"] = mapper_address


def load_example_data(download_folder="/data"):
    data_path = os.path.join(download_folder, "OpenSlide_adapted")
    zip_file = os.path.join(download_folder, "testdata.zip")
    if not os.path.exists(zip_file) or os.path.getsize(zip_file) != 16182556021:
        print("Beginning file download (16 GB)...")
        url = "https://nextcloud.empaia.org/s/4fpdFEn69gqgrgK/download"
        urlretrieve(url, zip_file)
        extract_zip_file(zip_file, download_folder)
    elif not os.path.exists(data_path) or len(os.listdir(data_path)) != 11:
        extract_zip_file(zip_file, download_folder)
    return data_path


def extract_zip_file(zip_file, download_folder):
    with zipfile.ZipFile(zip_file, "r") as zip_ref:
        zip_ref.extractall(download_folder)


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
    parser.add_argument("--mapper-address", default=default_mapper_address, help="Mapper-Service Address")
    args = parser.parse_args()

    if not os.path.exists(args.data_dir):
        print(f"Not a valid directory [{args.data_dir}]. Create directory first.")
    else:
        if args.load_example_data:
            # we load the example data and add subpath OpenSlide_adapted to our data path
            args.data_dir = load_example_data(args.data_dir)

        set_env_from_args(args.data_dir, args.mapper_address, args.mapper_address == default_mapper_address)
        uvicorn.run("wsi_service.api:api", host="0.0.0.0", port=int(args.port), reload=args.debug)


if __name__ == "__main__":
    main()
