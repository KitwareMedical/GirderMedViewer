from enum import Enum
from typing import Any


class DataclassEnum(Enum):
    @staticmethod
    def encoder(object: Enum):
        return object.value

    @classmethod
    def decoder(cls, value: Any):
        return cls(value)


class SegmentationEffectType(DataclassEnum):
    PAINT = "Paint"
    ERASE = "Erase"
    UNDEFINED = "No tool"


class FilterType(DataclassEnum):
    SEGMENTATION = "segmentation"
    GAUSSIAN_BLUR = "gaussian blur"
    UNDEFINED = None


class SceneObjectType(DataclassEnum):
    MESH = "mesh"
    VOLUME = "volume"
    UNDEFINED = None


class VolumeObjectType(DataclassEnum):
    SCALAR = "scalar_volume"
    VECTOR = "vector_volume"
    LABELMAP = "labelmap_volume"
    UNDEFINED = None
