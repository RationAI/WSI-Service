import importlib

from .default import Default


def get_api_integration(settings, logger, http_client):
    if settings.api_v3_integration:
        module_name, class_name = settings.api_v3_integration.split(":")
        module = importlib.import_module(module_name)
        IntegrationClass = getattr(module, class_name)
        return IntegrationClass(settings=settings, logger=logger, http_client=http_client)

    return Default(settings=settings, logger=logger, http_client=http_client)
