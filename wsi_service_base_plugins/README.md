# Plugin Development

Plugins can be developed simply by implementing the Slide interface (see any of the plugin implementation).

The documentation here only describes the integration. To integrate a new plugin, do:
 - modify ``Dockerfile``s to include your plugin in the build procedure
 - modify ``myplugin/pyproject.toml`` with your dependencies, possibly install deps also within Docker (e.g. Java dependency)
 - modify **base** file ``pyproject.toml`` to add your plugin definition so the wsi service will recognize it:
   ````python
    wsi-service-plugin-openslide = { path = "wsi_service_base_plugins/openslide", develop = true }
    wsi-service-plugin-pil = { path = "wsi_service_base_plugins/pil", develop = true }
    wsi-service-plugin-tifffile = { path = "wsi_service_base_plugins/tifffile", develop = true }
    wsi-service-plugin-[my-plugin-name] = { path = [YOUR PLUGIN PATH], develop = true }
    ...
   ````
- within ``__init__.py`` file, do:
   ````python
  # as registered within pyptoject toml!
  from wsi_service_plugin_[my_plugin_name].slide import Slide
  
  # optional callback, executed at thread start, if not defined not executed
  def start():
      pass
  
  # optional callback, executed at thread stop, if not defined not executed
  def stop():
      pass
  
  # predicate that drives which files will be handled by this plugin
  def is_supported(filepath):
      return True
  
  # must return a Slide interface implementation
  async def open(filepath):
      return await Slide.create(filepath)

   ````