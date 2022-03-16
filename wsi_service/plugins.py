import collections
import importlib
import os
import pathlib
import pkgutil
from importlib.metadata import version as version_from_name

from wsi_service.service_status import PluginInfo
from wsi_service.singletons import settings

# check for plugins
plugins = {
    name.replace("wsi_service_plugin_", ""): importlib.import_module(name)
    for finder, name, ispkg in pkgutil.iter_modules()
    if name.startswith("wsi_service_plugin_")
}


async def load_slide(filepath):
    if not (os.path.exists(filepath)):
        raise FileNotFoundError(f"File {filepath} not found.")
    file_extension = _get_file_extension(filepath)
    available_plugins_for_image_file_extension = _get_available_plugins_for_image_file_extension(file_extension)
    if len(available_plugins_for_image_file_extension) == 0:
        raise ModuleNotFoundError(f"There is no plugin available for file extension {file_extension}.")

    selected_plugin_name = ""
    if file_extension in settings.plugins_default:
        selected_plugin_name = settings.plugins_default[file_extension]

    if selected_plugin_name:
        if selected_plugin_name in available_plugins_for_image_file_extension:
            seletected_plugin = available_plugins_for_image_file_extension[selected_plugin_name]
        else:
            raise ModuleNotFoundError(
                f"Selected plugin {selected_plugin_name} is not available. Please install or specify another plugin."
            )
    else:
        selected_plugin_name, seletected_plugin = next(iter(available_plugins_for_image_file_extension.items()))
    try:
        slide = await seletected_plugin.open(filepath)
    except Exception as e:
        print(f"Plugin {selected_plugin_name} unable to open image")
        raise e
    return slide


def is_supported_format(filepath):
    file_extension = _get_file_extension(filepath)
    return file_extension in _get_supported_file_extensions()


def get_plugins_overview():
    plugins_overview = []
    for plugin_name, plugin_item in plugins.items():
        version = version_from_name("wsi_service_plugin_" + plugin_name)
        plugin = PluginInfo(
            name=plugin_name, version=version, supported_file_extensions=sorted(plugin_item.supported_file_extensions)
        )
        plugins_overview.append(plugin)
    return plugins_overview


def _get_supported_file_extensions():
    supported_file_extensions = []
    for plugin in plugins.values():
        supported_file_extensions += plugin.supported_file_extensions
    return supported_file_extensions


def _get_file_extension(filepath):
    file_extension = pathlib.Path(filepath).suffix
    if ".ome" + file_extension in filepath:
        file_extension = ".ome" + file_extension
    return file_extension


def _get_available_plugins_for_image_file_extension(file_extension):
    available_plugins_for_image_file_extension = {}
    for plugin_name, plugin_item in plugins.items():
        if file_extension in plugin_item.supported_file_extensions:
            available_plugins_for_image_file_extension[plugin_name] = plugin_item
    return available_plugins_for_image_file_extension


def _get_duplicate_items(list_input):
    return [item for item, count in collections.Counter(list_input).items() if count > 1]


def _validate_plugins_default():
    # check plugin is available
    for file_extension, plugin_default in settings.plugins_default.items():
        if plugin_default not in plugins:
            raise ModuleNotFoundError(f"Unknown plugin {plugin_default} specified for {file_extension}.")
    supported_file_extensions = _get_supported_file_extensions()
    ambiguous_file_extensions = _get_duplicate_items(supported_file_extensions)
    # check for conflicts
    for file_extension in ambiguous_file_extensions:
        available_plugins_for_image_file_extension = _get_available_plugins_for_image_file_extension(file_extension)
        if len(available_plugins_for_image_file_extension) > 1 and file_extension not in settings.plugins_default:
            other_plugin_options = "\n".join(["- " + p for p in available_plugins_for_image_file_extension])
            raise Exception(
                f"There is more than one plugin available for file extension {file_extension}.\nPlease specify one of the following plugins as default in the settings:\n{other_plugin_options}"
            )


_validate_plugins_default()
