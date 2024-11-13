from .alive import add_routes_alive
from .viewer import add_routes_viewer


def add_routes_root(app, settings):
    add_routes_alive(app, settings)
    if settings.enable_viewer_routes:
        add_routes_viewer(app, settings)
