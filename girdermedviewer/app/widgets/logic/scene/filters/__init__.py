from ....utils import FilterType
from .gaussian_filter_logic import GaussianFilterLogic

FILTER_MAP = {FilterType.GAUSSIAN_BLUR: GaussianFilterLogic}

__all__ = ["FILTER_MAP"]
