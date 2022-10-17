from fastapi import status

from wsi_service.plugins import get_plugins_overview
from wsi_service.service_status import WSIServiceStatus


def add_routes(app, settings):
    @app.get("/alive", response_model=WSIServiceStatus, status_code=status.HTTP_200_OK)
    async def _():
        return WSIServiceStatus(
            status="ok",
            version=settings.version,
            plugins=get_plugins_overview(),
            plugins_default=settings.plugins_default,
        )
