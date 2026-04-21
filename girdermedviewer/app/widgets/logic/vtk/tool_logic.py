import logging

from trame_server import Server
from vtk import vtkImageData

from ...ui import ToolState, ToolType, ToolUI
from ..base_logic import BaseLogic
from ..scene.scene_logic import SceneLogic
from .tools.place_roi_logic import PlaceROILogic
from .tools.segmentation_effect_logic import SegmentationEffectLogic
from .views_logic import ViewsLogic

logger = logging.getLogger(__name__)


class ToolLogic(BaseLogic[ToolState]):
    def __init__(self, server: Server, views_logic: ViewsLogic, scene_logic: SceneLogic) -> None:
        super().__init__(server, ToolState)
        self._views_logic = views_logic
        self._views_logic.object_added.connect(self._on_object_added)
        self._views_logic.primary_volume_added.connect(self._on_primary_volume_added)

        self._scene_logic = scene_logic
        self._scene_logic.segment_selected.connect(self._on_segment_selected)

        # ROI tool
        self._roi_logic = PlaceROILogic(self.server, self._views_logic)

        # Segmentation tool
        self._segmentation_logic = SegmentationEffectLogic(self.server, self._views_logic)
        self._scene_logic.segment_selected.connect(self._segmentation_logic.set_active_segment)
        self._scene_logic.segment_cleared.connect(self._segmentation_logic.clear_segment)

        # Watchers
        self.bind_changes({self.name.active_tool: self._on_tool_change})
        self._views_logic.bind_changes({self._views_logic.name.is_viewer_disabled: self._on_viewer_status_changed})

    def _reset_tool_state(self):
        self._typed_state.set_dataclass(ToolState())

    def _on_object_added(self) -> None:
        self.data.is_toolbar_disabled = False

    def _on_primary_volume_added(self, image_data: vtkImageData) -> None:
        self.data.is_oblique_tool_disabled = False
        self.data.is_point_tool_disabled = False
        self.data.is_roi_tool_disabled = False
        self._roi_logic.set_default_bounds(image_data.GetBounds())
        self._segmentation_logic.set_paint_effects(self._views_logic.slice_views)

    def _on_segment_selected(self, _image_data: vtkImageData | None, value: int):
        if value == 0:
            self.data.is_segmentation_tool_disabled = True
            self.data.active_tool = ToolType.UNDEFINED
        else:
            self.data.is_segmentation_tool_disabled = False
            self.data.active_tool = ToolType.SEGMENTATION_EFFECT

    def _on_viewer_status_changed(self, is_viewer_disabled: bool) -> None:
        if is_viewer_disabled:
            self._reset_tool_state()

    def _on_tool_change(self, active_tool: ToolType) -> None:
        self._roi_logic.set_enabled(active_tool == ToolType.PLACE_ROI)
        self._segmentation_logic.set_enabled(active_tool == ToolType.SEGMENTATION_EFFECT)
        self._views_logic.update_views()

    def set_ui(self, ui: ToolUI) -> None:
        ui.reset_clicked.connect(self._views_logic.reset)

        self._roi_logic.set_ui(ui.place_roi_ui)
