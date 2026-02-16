from enum import Enum
from typing import Any


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
