from ...utils.lib_utils import get_class
from ...singletons import logger, settings
from .integrations import get_api_integration

api_integration = get_api_integration(settings=settings, logger=logger, http_client=None)

MapperClass = get_class(settings.local_mode) if settings.local_mode else None
