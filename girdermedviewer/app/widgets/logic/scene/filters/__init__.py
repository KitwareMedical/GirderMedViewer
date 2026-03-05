from ....utils import FilterType
from .gaussian_filter_logic import GaussianFilterLogic
from .segmentation_filter_logic import SegmentationFilterLogic

FILTER_MAP = {FilterType.GAUSSIAN_BLUR: GaussianFilterLogic, FilterType.SEGMENTATION: SegmentationFilterLogic}

__all__ = ["FILTER_MAP"]
