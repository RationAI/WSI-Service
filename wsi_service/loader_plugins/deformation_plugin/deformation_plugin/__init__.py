try:
    from .deformation import Deformation
except ModuleNotFoundError:
    print("Deformation module could not be loaded. Aborting tests.")
