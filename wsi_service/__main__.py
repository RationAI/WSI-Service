import argparse
import os
import sys
from urllib.request import urlretrieve

from werkzeug.serving import is_running_from_reloader

from wsi_service.application import create_app

parser = argparse.ArgumentParser(description='Webserice that serves histological whole-slide-images')
parser.add_argument('data_dir', help='Base path to histo data')
parser.add_argument('--port', default=8080, help='Port the WSI-Service listens to')
parser.add_argument('--debug', dest='debug', action='store_true', help='Use the debug config')
parser.add_argument('--load-example-data', dest='load_example_data', action='store_true', help='This will download an example image into the data folder before starting the server')
parser.add_argument('--mapper-address', default='http://mapper-service:8000/slides/{global_slide_id}', help='Mapper-Service Address')
parser.add_argument('--local-mode', dest='local_mode', action='store_true', help='Run WSI-Service in local mode with a minimal local filesystem mapper. Local mode ignores --mapper-address.')
args = parser.parse_args()

if args.load_example_data and not is_running_from_reloader():
    os.mkdir('/data/example')
    print('Beginning file download (169.33MB)...')
    url = 'http://openslide.cs.cmu.edu/download/openslide-testdata/Aperio/CMU-1.svs'
    urlretrieve(url, '/data/example/CMU-1.svs')
    print('Done')


config_class_string = 'wsi_service.config.Debug' if args.debug else 'wsi_service.config.Production'
if args.local_mode:
    app = create_app('http://localhost:8080/api/v1/slides/{global_slide_id}', args.data_dir, config_class_string)
else:
    app = create_app(args.mapper_address, args.data_dir, config_class_string)
app.run('0.0.0.0', port=args.port, threaded=True, debug=args.debug)
