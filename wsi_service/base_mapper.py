from abc import ABC, abstractmethod


class BaseMapper(ABC):
    """
    Abstract base class for all local mappers.
    Provides common attributes and defines the interface that all mappers must implement.
    """

    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.is_context_dependent = False

    @abstractmethod
    def get_cases(self, context=None):
        raise NotImplementedError

    @abstractmethod
    def get_slides(self, case_id):
        raise NotImplementedError

    @abstractmethod
    def get_slide(self, slide_id):
        raise NotImplementedError

    # Used only by context-independent mappers
    def refresh(self, force_refresh=True):
        return None

    def load(self):
        return None
