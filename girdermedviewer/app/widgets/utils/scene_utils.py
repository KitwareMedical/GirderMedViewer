from enum import Enum
from typing import Any


class FilterType(Enum):
    SEGMENTATION = "segmentation"
    GAUSSIAN_BLUR = "gaussian blur"
    UNDEFINED = None

    @staticmethod
    def encoder(object: Enum):
        return object.value

    @classmethod
    def decoder(cls, value: Any):
        return cls(value)


class SceneObjectType(Enum):
    MESH = "mesh"
    VOLUME = "volume"
    UNDEFINED = None

    @staticmethod
    def encoder(object: Enum):
        return object.value

    @classmethod
    def decoder(cls, value: Any):
        return cls(value)


class VolumeLayer(Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    UNDEFINED = None


ICONS_MAP = {
    FilterType.SEGMENTATION: "mdi-shape",
    FilterType.GAUSSIAN_BLUR: "mdi-blur",
    SceneObjectType.MESH: "mdi-vector-polyline",
    SceneObjectType.VOLUME: "mdi-grid",
}
