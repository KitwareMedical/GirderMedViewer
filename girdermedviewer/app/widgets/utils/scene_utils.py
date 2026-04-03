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
    STREAMLINE = "streamline"
    UNDEFINED = None


class SceneObjectType(DataclassEnum):
    MESH = "mesh"
    VOLUME = "volume"
    UNDEFINED = None


class VolumeLayer(DataclassEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    UNDEFINED = None


class SceneObjectSubtype(DataclassEnum):
    SCALAR = "scalar_volume"
    VECTOR = "vector_volume"
    LABELMAP = "labelmap_volume"
    STREAMLINE = "streamline_mesh"
    UNDEFINED = None


ICONS_MAP = {
    FilterType.SEGMENTATION: "mdi-shape",
    FilterType.GAUSSIAN_BLUR: "mdi-blur",
    FilterType.STREAMLINE: "mdi-asterisk",
    SceneObjectType.MESH: "mdi-vector-polyline",
    SceneObjectType.VOLUME: "mdi-grid",
}
