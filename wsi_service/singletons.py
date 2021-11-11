import logging

from .settings import Settings

settings = Settings()


for logger_name in ["uvicorn.error", "uvicorn.access", "uvicorn"]:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    if settings.debug:
        logger.setLevel(logging.DEBUG)
    if len(logger.handlers) > 0:
        formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        logger.handlers[0].setFormatter(formatter)
