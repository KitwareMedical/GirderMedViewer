from typing import Any

from trame_server.core import Server
from undo_stack import Signal
from vtk import vtkImageData, vtkPolyData

from girdermedviewer.app.widgets.logic.vtk.handlers.volume_handler import VolumeHandler

from ...logic.base_logic import BaseLogic
from ...ui import ViewsState, ViewsUI, ViewType
from ...utils import (
    SceneObjectSubtype,
    VolumeLayer,
    get_color_preset_parser,
    get_volume_preset_parser,
)
from ..scene.objects.volume_object_logic import VolumeDisplay
from .views.slice_view_logic import SliceViewLogic
from .views.threed_view_logic import ThreeDViewLogic
from .views.view_logic import ViewLogic


class ViewsLogic(BaseLogic[ViewsState]):
    window_level_changed = Signal()
    object_added = Signal()
    all_objects_removed = Signal()
    primary_volume_added = Signal(vtkImageData)

    def __init__(self, server: Server) -> None:
        super().__init__(server, ViewsState)
        self.view_logics: dict[ViewType, ViewLogic[VolumeHandler]] = {}

        self.volume_preset_parser = get_volume_preset_parser()
        self.color_preset_parser = get_color_preset_parser()

        for view_type in ViewType:
            view_logic_type = ThreeDViewLogic if view_type == ViewType.THREED else SliceViewLogic
            self.view_logics[view_type] = view_logic_type(
                server=self.server,
                view_type=view_type,
                volume_preset_parser=self.volume_preset_parser,
                color_preset_parser=self.color_preset_parser,
            )
            self.view_logics[view_type].window_level_changed.connect(self.window_level_changed)

    @property
    def views(self) -> list[ViewLogic[VolumeHandler]]:
        return list(self.view_logics.values())

    @property
    def slice_views(self) -> list[SliceViewLogic]:
        return [view for view in self.view_logics.values() if isinstance(view, SliceViewLogic)]

    @property
    def threed_views(self) -> list[ThreeDViewLogic]:
        return [view for view in self.view_logics.values() if isinstance(view, ThreeDViewLogic)]

    def _reset_view_state(self):
        self._typed_state.set_dataclass(ViewsState())

    def _on_object_added(self) -> None:
        if self.data.is_viewer_disabled:
            self.data.is_viewer_disabled = False
            self.object_added()

        self.update_views()

    def _on_object_removed(self) -> None:
        has_object = False

        for view_logic in self.slice_views:
            has_object = (
                view_logic.volume_handler.has_primary_volume()
                or view_logic.volume_handler.has_secondary_volume()
                or view_logic.mesh_handler.has_mesh()
                or has_object
            )

        if not has_object:
            self._reset_view_state()
            self.all_objects_removed()

        self.update_views()

    def _is_view_shown(self, view_logic: ViewLogic[VolumeHandler]) -> bool:
        return self.data.fullscreen is None or self.data.fullscreen == view_logic.type

    def update_views(self) -> None:
        for view in self.views:
            if self._is_view_shown(view):
                view.update()

    def update_slice_views(self) -> None:
        for view in self.slice_views:
            if self._is_view_shown(view):
                view.update()

    def set_ui(self, ui: ViewsUI):
        # Connect view logics to UI
        for view_type, view_ui in ui.view_uis.items():
            view_logic = self.view_logics.get(view_type)
            if view_logic is not None:
                view_logic.set_ui(view_ui)

    def reset(self) -> None:
        for view_logic in self.views:
            view_logic.reset()
        self.update_views()

    def add_mesh(self, data_id: str, poly_data: vtkPolyData, display_properties: VolumeDisplay) -> None:
        for view_logic in self.views:
            view_logic.add_mesh(data_id, poly_data, display_properties)

        self._on_object_added()

    def remove_mesh(self, data_id: str, only_data: Any = None) -> None:
        for view_logic in self.views:
            view_logic.remove_mesh(data_id, only_data)

        self._on_object_removed()

    def add_volume(
        self,
        data_id: str,
        image_data: vtkImageData,
        display_properties: VolumeDisplay,
        layer: VolumeLayer,
        subtype: SceneObjectSubtype,
    ):
        for view_logic in self.views:
            view_logic.add_volume(data_id, image_data, display_properties, layer, subtype)

        self._on_object_added()

        if layer == VolumeLayer.PRIMARY:
            self.data.are_obliques_visible = True
            self.data.are_sliders_visible = True
            self.primary_volume_added(image_data)

    def remove_volume(self, data_id: str, only_data: Any = None) -> None:
        for view_logic in self.views:
            view_logic.remove_volume(data_id, only_data)

        self._on_object_removed()
