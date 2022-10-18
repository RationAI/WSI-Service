from .alive import add_routes_alive
from .local_mode import add_routes_local_mode
from .viewer import add_routes_viewer


def add_routes_root(app, settings):
    add_routes_alive(app, settings)
    if settings.local_mode:
        add_routes_local_mode(app, settings)
    if settings.enable_viewer_routes:
        add_routes_viewer(app, settings)
