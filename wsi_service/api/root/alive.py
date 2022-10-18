from fastapi import status

from wsi_service.custom_models.service_status import WSIServiceStatus
from wsi_service.plugins import get_plugins_overview


def add_routes_alive(app, settings):
    @app.get("/alive", tags=["Server"], response_model=WSIServiceStatus, status_code=status.HTTP_200_OK)
    async def _():
        return WSIServiceStatus(
            status="ok",
            version=settings.version,
            plugins=get_plugins_overview(),
            plugins_default=settings.plugins_default,
        )
