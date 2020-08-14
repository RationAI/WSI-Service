import logging

from flask import Flask, redirect, request, url_for
from flask_talisman import Talisman

import wsi_service
from flasgger import Swagger, LazyString
from wsi_service.api import create_blueprint
from wsi_service.api_utils import SignedIntConverter


def init_swagger(app):
    template = {
        "info": {
            "title": "WSI-Service",
            "description": "EMPAIA WSI-Service to stream whole slide images",
            "contact": {
                "responsibleOrganization": "Fraunhofer MEVIS",
                "responsibleDeveloper": "Henning Höfener",
                "email": "henning.hoefener@mevis.fraunhofer.de",
                "url": "www.mevis.fraunhofer.de",
            },
            "version": wsi_service.__version__
        }
    }
    Swagger(app, template=template)

def create_app(data_dir, config_class_string):
    app = Flask(__name__)
    app.config.from_object(config_class_string)
    app.config['DATA_DIR'] = data_dir

    # add signed_int url type
    app.url_map.converters['signed_int'] = SignedIntConverter

    # also accept urls with trailing slashes
    app.url_map.strict_slashes = False

    # CSP needs exception for swagger ui
    content_security_policy={
        'default-src': "'self'",
        'script-src': ["'self'", "'unsafe-inline'"],
        'style-src': ["'self'", "'unsafe-inline'"]
    }
    Talisman(app, force_https=False, session_cookie_secure=False, content_security_policy=content_security_policy)

    url_prefix = '/api/v1'
    app.register_blueprint(create_blueprint('api', app.config, swagger_tags=[url_prefix]), url_prefix=url_prefix)
    init_swagger(app)

    # redirect to apidocs
    @app.route('/')
    def index():
        return redirect('/apidocs')

    return app

def stop():
    shutdown_func = request.environ.get('werkzeug.server.shutdown')
    if shutdown_func is not None:
        shutdown_func()
