import logging

from .settings import Settings

settings = Settings()


logger = logging.getLogger(logger_name)
logger.setLevel(logging.INFO)
if settings.debug:
    logger.setLevel(logging.DEBUG)
