from trame_server.core import Server
from trame_server.utils.typed_state import TypedState
from undo_stack import Signal
from vtk import vtkImageData, vtkPolyData

from ...logic.base_logic import BaseLogic
from ...ui import ToolState, ToolType, ToolUI, ViewsState, ViewsUI, ViewType
from ...utils import (
    VolumeLayer,
    get_color_preset_parser,
    get_volume_preset_parser,
)
from .place_roi_logic import PlaceROILogic
from .views.slice_view_logic import SliceViewLogic
from .views.threed_view_logic import ThreeDViewLogic
from .views.view_logic import ViewLogic


class ViewsLogic(BaseLogic[ViewsState]):
    window_level_changed = Signal()

    def __init__(self, server: Server):
        super().__init__(server, ViewsState)
        self.view_logics: dict[ViewType, ViewLogic] = {}
        self.ctrl.reset = self.reset

        self.volume_preset_parser = get_volume_preset_parser()
        self.color_preset_parser = get_color_preset_parser()

        self._tool_state = TypedState(self.state, ToolState)
        self._tool_state.bind_changes({self._tool_state.name.active_tool: self._on_tool_change})

        self.roi_logic = PlaceROILogic(self.server)

        for view_type in ViewType:
            view_logic_type = ThreeDViewLogic if view_type == ViewType.THREED else SliceViewLogic
            self.view_logics[view_type] = view_logic_type(
                server=self.server,
                view_type=view_type,
                volume_preset_parser=self.volume_preset_parser,
                color_preset_parser=self.color_preset_parser,
            )
            self.view_logics[view_type].window_level_changed.connect(self.window_level_changed)

    def _on_tool_change(self, active_tool: ToolType):
        self.roi_logic.enable_widget(active_tool == ToolType.PLACE_ROI)
        for view_logic in self.view_logics.values():
            if isinstance(view_logic, SliceViewLogic):
                view_logic.mesh_handler.set_mesh_visibility(self.roi_logic._id, active_tool == ToolType.PLACE_ROI)
        self.update_views()

    def set_ui(self, ui: ViewsUI, tool_ui: ToolUI):
        # Link VtkRemoteView update method
        self.update_views = ui.update_views
        self.roi_logic.roi_updated.connect(self.update_views)

        # Connect logics to UI
        for view_type, view_ui in ui.view_uis.items():
            view_logic = self.view_logics.get(view_type)
            if view_logic is not None:
                view_logic.set_ui(view_ui)
        self.roi_logic.set_ui(tool_ui.place_roi_ui)

        # Init ROI
        self._init_roi()

    def reset(self):
        for view_logic in self.view_logics.values():
            view_logic.reset()
        self.update_views()

    def add_mesh(self, data_id: str, poly_data: vtkPolyData):
        for view_logic in self.view_logics.values():
            view_logic.add_mesh(data_id, poly_data)

    def add_volume(self, data_id: str, image_data: vtkImageData, layer: VolumeLayer):
        if layer == VolumeLayer.PRIMARY:
            self.data.are_obliques_visible = True
            self.roi_logic.set_default_bounds(image_data.GetBounds())
        for view_logic in self.view_logics.values():
            view_logic.add_volume(data_id, image_data, layer)

    def _init_roi(self):
        for view_logic in self.view_logics.values():
            view_logic.init_roi(self.roi_logic)
