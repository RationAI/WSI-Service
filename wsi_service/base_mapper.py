from abc import ABC, abstractmethod
from typing import List, Optional

from wsi_service.custom_models.local_mapper_models import CaseLocalMapper, SlideLocalMapper


class BaseMapper(ABC):
    """
    Abstract base class for all local mappers.
    Provides common attributes and defines the interface that all mappers must implement.
    """

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.is_context_dependent: bool = False

    @abstractmethod
    def get_cases(self, context: Optional[str] = None) -> List[CaseLocalMapper]:
        raise NotImplementedError

    @abstractmethod
    def get_slides(self, case_id: str) -> List[SlideLocalMapper]:
        raise NotImplementedError

    @abstractmethod
    def get_slide(self, slide_id: str) -> SlideLocalMapper:
        raise NotImplementedError

    # Used only by context-independent mappers
    def refresh(self, force_refresh: bool = True) -> None:
        return None

    def load(self) -> None:
        return None
