import logging
from collections.abc import Callable

from trame_dataclass.v2 import get_instance
from trame_server.core import Server

from ....utils import DataArray, MeshColoringMode, debounce, supported_mesh_extensions
from ...vtk.views_logic import ViewsLogic
from ..objects.mesh_object_logic import MeshDisplay, MeshObjectLogic
from .object_handler import ObjectHandler

logger = logging.getLogger(__name__)


class MeshDisplayHandler:
    def __init__(self, views_logic: ViewsLogic):
        self.views_logic = views_logic

    def update_visibility(self, mesh_id: str) -> Callable:
        @debounce(0.05)
        def _update_visibility(visible: bool) -> None:
            for view in self.views_logic.views:
                modified = view.mesh_handler.set_mesh_visibility(mesh_id, visible)
                if modified:
                    view.update()

        return _update_visibility

    def update_opacity(self, mesh_id: str) -> Callable:
        @debounce(0.05)
        def _update_opacity(opacity: float) -> None:
            for view in self.views_logic.views:
                modified = view.mesh_handler.set_mesh_opacity(mesh_id, opacity)
                if modified:
                    view.update()

        return _update_opacity

    def update_solid_coloring(self, mesh_id: str) -> Callable:
        @debounce(0.05)
        def _update_solid_coloring(color: str) -> None:
            for view in self.views_logic.views:
                modified = view.mesh_handler.set_mesh_solid_color(mesh_id, color)
                if modified:
                    view.update()

        return _update_solid_coloring

    def update_array_coloring(self, mesh_id: str, mesh_display: MeshDisplay) -> Callable:
        @debounce(0.05)
        def _update_array_coloring(name: str, is_inverted: bool, scalar_range: list[float]) -> None:
            active_array = get_instance(mesh_display.active_array_id)
            for view in self.views_logic.views:
                modified = view.mesh_handler.set_mesh_array_color(
                    mesh_id,
                    active_array,
                    name,
                    is_inverted,
                    scalar_range,
                )
                if modified:
                    view.update()

        return _update_array_coloring

    def update_active_array(self, mesh_id: str, mesh_display: MeshDisplay) -> Callable:
        @debounce(0.05)
        def _update_active_array(active_array_id: str) -> None:
            active_array = get_instance(active_array_id)
            assert isinstance(active_array, DataArray)
            if active_array.coloring_mode == MeshColoringMode.SOLID:
                self.update_solid_coloring(mesh_id)(mesh_display.solid_color)

            elif active_array.coloring_mode == MeshColoringMode.ARRAY:
                mesh_display.array_color.array_range = active_array.array_min_max

        return _update_active_array


class MeshHandler(ObjectHandler):
    def __init__(self, server: Server, views_logic: ViewsLogic):
        super().__init__(server, views_logic)
        self.display_handler = MeshDisplayHandler(views_logic)

    @property
    def supported_extensions(self) -> tuple[str]:
        return supported_mesh_extensions()

    def _connect_mesh_logic_to_display_handler(self, mesh_logic: MeshObjectLogic):
        mesh_logic.display.watch(("opacity",), self.display_handler.update_opacity(mesh_logic._id))
        mesh_logic.display.watch(
            ("active_array_id",), self.display_handler.update_active_array(mesh_logic._id, mesh_logic.display)
        )
        mesh_logic.display.watch(("solid_color",), self.display_handler.update_solid_coloring(mesh_logic._id))
        mesh_logic.display.array_color.watch(
            ("name", "is_inverted", "array_range"),
            self.display_handler.update_array_coloring(mesh_logic._id, mesh_logic.display),
        )
        mesh_logic.scene_object.watch(("is_visible",), self.display_handler.update_visibility(mesh_logic._id))

    def add_object_to_views(self, mesh_logic: MeshObjectLogic) -> None:
        self.object_logics[mesh_logic._id] = mesh_logic
        self._connect_mesh_logic_to_display_handler(mesh_logic)
        self.views_logic.add_mesh(mesh_logic._id, mesh_logic.object_data, mesh_logic.display)

    def remove_object_from_views(self, mesh_logic: MeshObjectLogic) -> None:
        mesh_logic.display.clear_watchers()
        self.object_logics.pop(mesh_logic._id)
        self.unregister_object_from_views(mesh_logic)

    def unregister_object_from_views(self, mesh_logic: MeshObjectLogic) -> None:
        self.views_logic.remove_mesh(mesh_logic._id)

    def set_object_visibility(self, mesh_logic: MeshObjectLogic, visible: bool) -> None:
        mesh_logic.scene_object.is_visible = visible
