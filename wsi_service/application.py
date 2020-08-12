import logging

from flask import Flask, redirect, request, url_for
from flask_talisman import Talisman

from wsi_service.api import create_blueprint
from wsi_service.api_utils import SignedIntConverter


def create_app(data_dir, config_class_string):
    app = Flask(__name__)
    app.config.from_object(config_class_string)
    app.config['DATA_DIR'] = data_dir

    # add signed_int url type
    app.url_map.converters['signed_int'] = SignedIntConverter

    # also accept urls with trailing slashes
    app.url_map.strict_slashes = False

    Talisman(app, force_https=False, session_cookie_secure=False)
    app.register_blueprint(create_blueprint('api', app.config), url_prefix='/api/v1')

    # redirect to current api root
    @app.route('/')
    def index():
        return redirect(url_for('api.get_server_info'))

    return app

def stop():
    shutdown_func = request.environ.get('werkzeug.server.shutdown')
    if shutdown_func is not None:
        shutdown_func()
