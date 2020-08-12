import argparse
import sys

from wsi_service.application import create_app

parser = argparse.ArgumentParser(description='webserice that serves histological whole-slide-images')
parser.add_argument('data_dir', help='path to histo data, should point to directory with folders as cases')
parser.add_argument('--port', default=8080, help='Port the WSI-Service listens to')
parser.add_argument('--debug', dest='debug', action='store_true', help='Use the debug config')
args = parser.parse_args()

config_class_string = 'wsi_service.config.Debug' if args.debug else 'wsi_service.config.Production'
app = create_app(args.data_dir, config_class_string)
app.run('0.0.0.0', port=args.port, threaded=True)
