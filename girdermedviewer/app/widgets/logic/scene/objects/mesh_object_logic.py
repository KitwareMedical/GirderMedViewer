import logging

from trame_dataclass.v2 import StateDataModel, Sync

from ....utils import (
    SceneObjectType,
    get_random_color,
    load_mesh,
)
from .scene_object_logic import SceneObjectLogic

logger = logging.getLogger(__name__)


class MeshDisplay(StateDataModel):
    color = Sync(str)
    opacity = Sync(float, 1.0)


class MeshObjectLogic(SceneObjectLogic):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.scene_object.object_type = SceneObjectType.MESH
        self.display = MeshDisplay(
            self.server,
            color=get_random_color(),
        )
        self.scene_object.display = self.display._id

    def load_object_data(self, file_path: str) -> None:
        self.object_data = load_mesh(file_path)
