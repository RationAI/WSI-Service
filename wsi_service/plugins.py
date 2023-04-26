import importlib
import os
import pathlib
import pkgutil
from importlib.metadata import version as version_from_name

from fastapi import HTTPException

from wsi_service.custom_models.service_status import PluginInfo

from wsi_service.singletons import logger

plugins = {
    name.replace("wsi_service_plugin_", ""): importlib.import_module(name)
    for _, name, _ in pkgutil.iter_modules()
    if name.startswith("wsi_service_plugin_")
}


async def load_slide(filepath, plugin=None):
    if not (os.path.exists(filepath)):
        raise HTTPException(status_code=500, detail=f"File {filepath} not found.")

    logger.debug(f"Filepath: {filepath}")

    supported_plugins = _get_supported_plugins(filepath)
    logger.debug(f"[load_slide] Supported plugins: {supported_plugins}")
    if len(supported_plugins) == 0:
        raise HTTPException(status_code=500, detail="There is no plugin available that does support this slide.")

    if plugin:
        if plugin in supported_plugins.keys():
            return await _open_slide(supported_plugins[plugin], plugin, filepath)
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Selected plugin {plugin} is not available or does not support this slide. Please specify another plugin.",
            )

    exception_details = ""
    for plugin_name, plugin in _get_sorted_plugins():
        logger.debug(f"[load_slide] Checking plugin: {plugin_name} | {plugin}")
        try:
            return await _open_slide(plugin, plugin_name, filepath)
        except HTTPException as e:
            exception_details += e.detail + ". "
    raise HTTPException(status_code=500, detail=exception_details)


def get_plugins_overview():
    plugins_overview = []
    for plugin_name, plugin in plugins.items():
        version = version_from_name("wsi_service_plugin_" + plugin_name)
        plugin_info = PluginInfo(
            name=plugin_name, version=version, priority=_get_plugin_priority((plugin_name, plugin))
        )
        plugins_overview.append(plugin_info)
    return plugins_overview


def is_supported_format(filepath):
    return len(_get_supported_plugins(filepath)) > 0


def _get_supported_plugins(filepath):
    supported_plugins = {}
    for plugin_name, plugin in plugins.items():
        logger.debug(f"[_get_supported_plugins] Checking plugin: {plugin_name} | {plugin}")
        if _get_plugin_priority((plugin_name, plugin)) >= 0:
            logger.debug("[_get_supported_plugins] Plugin has priority >= 0")
            if hasattr(plugin, "is_supported"):
                logger.debug("[_get_supported_plugins] Check is_supported")
                if plugin.is_supported(filepath):
                    logger.debug(f"[_get_supported_plugins] Add plugin {plugin_name} to supported plugins")
                    supported_plugins[plugin_name] = plugin
            elif hasattr(plugin, "supported_file_extensions"):
                logger.debug("[_get_supported_plugins] Has supported_file_extensions")
                file_extension = pathlib.Path(filepath).suffix
                if file_extension in plugin.supported_file_extensions:
                    supported_plugins[plugin_name] = plugin
    logger.debug(f"[_get_supported_plugins] Supported plugins: {supported_plugins}")
    return supported_plugins


def _get_sorted_plugins():
    return sorted(plugins.items(), key=_get_plugin_priority, reverse=True)


def _get_plugin_priority(plugin_item):
    plugin_name = plugin_item[0]
    plugin = plugin_item[1]
    priority = getattr(plugin, "priority", 0)
    priority = os.environ.get(f"WS_PLUGIN_PRIORITY_{plugin_name.upper()}", priority)
    return int(priority)


async def _open_slide(plugin, plugin_name, filepath):
    try:
        slide = await plugin.open(filepath)
        slide.plugin = plugin_name
    except HTTPException as e:
        raise HTTPException(status_code=500, detail=f"Plugin {plugin_name} unable to open image ({e.detail})")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Plugin {plugin_name} unable to open image ({e})")
    return slide
