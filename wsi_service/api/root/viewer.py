import os
import pathlib

from fastapi.responses import HTMLResponse


def add_routes_viewer(app, settings):
    @app.get("/slides/{slide_id}/viewer", response_class=HTMLResponse, include_in_schema=False)
    async def _(slide_id: str):
        viewer_html = open(
            os.path.join(pathlib.Path(__file__).parent.absolute(), "viewer.html"), "r", encoding="utf-8"
        ).read()
        viewer_html = viewer_html.replace("REPLACE_SLIDE_ID", slide_id)
        return viewer_html

    if settings.local_mode:

        @app.get("/validation_viewer", response_class=HTMLResponse, include_in_schema=False)
        async def _():
            validation_viewer_html = open(
                os.path.join(pathlib.Path(__file__).parent.absolute(), "validation_viewer.html"), "r", encoding="utf-8"
            ).read()
            return validation_viewer_html
