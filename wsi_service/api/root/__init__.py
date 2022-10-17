from .alive import add_routes


def add_routes_root(app, settings):
    add_routes(app, settings)
