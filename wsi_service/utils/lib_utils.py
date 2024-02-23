import importlib


def get_class(class_descriptor: str):
    """ Get class from a module following class_descriptor (module.path:ClassName) """
    module_name, class_name = class_descriptor.split(":")
    module = importlib.import_module(module_name)
    return getattr(module, class_name)
