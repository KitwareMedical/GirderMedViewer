import logging

from trame_dataclass.v2 import (
    StateDataModel,
    Sync,
)
from trame_server import Server

from ....ui import VtkView
from ....utils import (
    SceneObjectType,
    debounce,
    get_random_color,
    load_mesh,
)
from .scene_object_logic import SceneObject, SceneObjectLogic

logger = logging.getLogger(__name__)

DEFAULT_VOLUME_PRESET_NAME = "CT-Cardiac3"


class MeshDisplay(StateDataModel):
    color = Sync(str)
    opacity = Sync(float, 1.0)


class MeshObjectLogic(SceneObjectLogic):
    def __init__(self, server: Server, scene_object: SceneObject, views: list[VtkView]) -> None:
        super().__init__(server, scene_object, views)
        self.scene_object.object_type = SceneObjectType.MESH
        self.display = MeshDisplay(
            self.server,
            color=get_random_color(),
        )
        self.scene_object.display = self.display._id

        self.display.watch(("opacity",), self._update_opacity)
        self.display.watch(("color",), self._update_color)

    @debounce(0.05)
    def _update_opacity(self, opacity: float) -> None:
        for view in self.views:
            view.set_mesh_opacity(self.scene_object._id, opacity)

    @debounce(0.05)
    def _update_color(self, color: str) -> None:
        hex = color.lstrip("#")
        color_tuple = tuple(float(int(hex[i : i + 2], 16)) / 255.0 for i in (0, 2, 4))
        for view in self.views:
            view.set_mesh_color(self.scene_object._id, color_tuple)

    def load(self, file_path: str) -> None:
        self.object_data = load_mesh(file_path)
        self.load_to_view()

        self.scene_object.gui.loading = False
