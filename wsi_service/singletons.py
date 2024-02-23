import logging

from pydantic import ValidationError

from .empaia_sender_auth import AioHttpClient, AuthSettings
from wsi_service.settings import Settings

settings = Settings()


logger = logging.getLogger("uvicorn")
logger.setLevel(logging.INFO)
if settings.debug:
    logger.setLevel(logging.DEBUG)

auth_settings = None
if settings.idp_url:
    try:
        auth_settings = AuthSettings(
            idp_url=settings.idp_url, client_id=settings.client_id, client_secret=settings.client_secret
        )
    except ValidationError as e:
        logger.info(f"Auth not configured: {e}")

http_client = AioHttpClient(
    logger=logger,
    auth_settings=auth_settings,
    chunk_size=settings.connection_chunk_size,
    timeout=settings.http_client_timeout,
    request_timeout=settings.request_timeout,
    connection_limit_per_host=settings.connection_limit_per_host,
)
