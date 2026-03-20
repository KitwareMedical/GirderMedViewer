import logging
from collections.abc import Callable

from ....ui import ViewUI, VtkView
from ....utils import debounce, supported_mesh_extensions
from ..objects.mesh_object_logic import MeshObjectLogic
from .object_handler import ObjectHandler

logger = logging.getLogger(__name__)


class MeshDisplayHandler:
    def __init__(self):
        self.views: list[VtkView] = []

    def update_visibility(self, mesh_id: str) -> Callable:
        @debounce(0.05)
        def _update_visibility(visible: bool) -> None:
            for view in self.views:
                view.set_mesh_visibility(mesh_id, visible)

        return _update_visibility

    def update_opacity(self, mesh_id: str) -> Callable:
        @debounce(0.05)
        def _update_opacity(opacity: float) -> None:
            for view in self.views:
                view.set_mesh_opacity(mesh_id, opacity)

        return _update_opacity

    def update_color(self, mesh_id: str) -> Callable:
        @debounce(0.05)
        def _update_color(color: str) -> None:
            hex = color.lstrip("#")
            color_tuple = tuple(float(int(hex[i : i + 2], 16)) / 255.0 for i in (0, 2, 4))
            for view in self.views:
                view.set_mesh_color(mesh_id, color_tuple)

        return _update_color

    def set_view_ui(self, view_ui: ViewUI):
        self.views = view_ui.views


class MeshHandler(ObjectHandler):
    def __init__(self, server):
        super().__init__(server)
        self.display_handler = MeshDisplayHandler()

    @property
    def supported_extensions(self) -> tuple[str]:
        return supported_mesh_extensions()

    def _connect_mesh_logic_to_display_handler(self, mesh_logic: MeshObjectLogic):
        mesh_logic.display.watch(("opacity",), self.display_handler.update_opacity(mesh_logic._id))
        mesh_logic.display.watch(("color",), self.display_handler.update_color(mesh_logic._id))
        mesh_logic.scene_object.watch(("is_visible",), self.display_handler.update_visibility(mesh_logic._id))

    def add_object_to_views(self, mesh_logic: MeshObjectLogic) -> None:
        self.object_logics[mesh_logic._id] = mesh_logic
        self._connect_mesh_logic_to_display_handler(mesh_logic)
        for view in self.views:
            view.add_mesh(mesh_logic._id, mesh_logic.object_data)

    def remove_object_from_views(self, mesh_logic: MeshObjectLogic) -> None:
        mesh_logic.display.clear_watchers()
        self.object_logics.pop(mesh_logic._id)
        self.unregister_object_from_views(mesh_logic)

    def set_object_visibility(self, mesh_logic: MeshObjectLogic, visible: bool) -> None:
        mesh_logic.scene_object.is_visible = visible

    def set_view_ui(self, view_ui: ViewUI) -> None:
        super().set_view_ui(view_ui)
        self.display_handler.set_view_ui(view_ui)
