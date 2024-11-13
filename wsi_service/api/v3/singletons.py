from ...utils.lib_utils import get_class
from ...singletons import http_client, logger, settings
from .integrations import get_api_integration

api_integration = get_api_integration(settings=settings, logger=logger, http_client=http_client)

MapperClass = get_class(settings.local_mode) if settings.local_mode else None
localmapper = MapperClass(settings.data_dir) if MapperClass else None
