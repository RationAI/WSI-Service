import importlib
import os
import pathlib
import pkgutil
from importlib.metadata import version as version_from_name

from fastapi import HTTPException

from wsi_service.custom_models.service_status import PluginInfo

plugins = {
    name.replace("wsi_service_plugin_", ""): importlib.import_module(name)
    for _, name, _ in pkgutil.iter_modules()
    if name.startswith("wsi_service_plugin_")
}


async def load_slide(filepath, plugin=None):
    if not (os.path.exists(filepath)):
        raise HTTPException(status_code=500, detail=f"File {filepath} not found.")

    supported_plugins = _get_supported_plugins(filepath)
    if len(supported_plugins) == 0:
        raise HTTPException(status_code=500, detail=f"There is no plugin available for that does support this slide.")

    if plugin:
        if supported_plugins[plugin].is_supported():
            return await _open_slide(supported_plugins[plugin], filepath)
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Selected plugin {plugin} is not available or does not support this slide. Please specify another plugin.",
            )

    exception_details = ""
    for plugin in _get_sorted_plugins(supported_plugins):
        try:
            return await _open_slide(plugin, filepath)
        except HTTPException as e:
            exception_details += e.detail + ". "
    raise HTTPException(status_code=500, detail=exception_details)


def get_plugins_overview():
    plugins_overview = []
    for plugin_name in plugins:
        version = version_from_name("wsi_service_plugin_" + plugin_name)
        plugin_info = PluginInfo(name=plugin_name, version=version)
        plugins_overview.append(plugin_info)
    return plugins_overview


def is_supported_format(filepath):
    return len(_get_supported_plugins(filepath))


def _get_supported_plugins(filepath):
    supported_plugins = {}
    for plugin_name, plugin in plugins.items():
        if hasattr(plugin, "is_supported"):
            if plugin.is_supported(filepath):
                supported_plugins[plugin_name] = plugin
        elif hasattr(plugin, "supported_file_extensions"):
            file_extension = pathlib.Path(filepath).suffix
            if file_extension in plugin.supported_file_extensions:
                supported_plugins[plugin_name] = plugin
    return supported_plugins


def _get_sorted_plugins(plugins):
    def __get_priority(plugin):
        if hasattr(plugin, "priority"):
            return plugin.priority
        else:
            return 0

    return sorted(plugins.values(), key=__get_priority, reverse=True)


async def _open_slide(plugin, filepath):
    try:
        slide = await plugin.open(filepath)
    except HTTPException as e:
        raise HTTPException(status_code=500, detail=f"Plugin {plugin} unable to open image ({e.detail})")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Plugin {plugin} unable to open image ({e})")
    return slide
