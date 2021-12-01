import logging

from .settings import Settings

settings = Settings()


logger = logging.getLogger("uvicorn")
logger.setLevel(logging.INFO)
if settings.debug:
    logger.setLevel(logging.DEBUG)
