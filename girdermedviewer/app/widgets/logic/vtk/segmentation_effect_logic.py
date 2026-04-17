import logging

from trame_dataclass.v2 import StateDataModel, Sync
from trame_server import Server
from undo_stack import Signal
from vtk import vtkImageData

from ...ui import SegmentationEffectState
from ...utils import SegmentationEffectType
from ...utils.vtk.segmentation import (
    BrushModel,
    BrushShape,
    LabelMapEditor,
    LabelMapOperation,
    SegmentPaintEffect2D,
)
from ..base_logic import BaseLogic
from .views.slice_view_logic import SliceViewLogic

logger = logging.getLogger(__name__)


class PaintEraseEffectProperties(StateDataModel):
    brush_size = Sync(int, 15)
    use_sphere_brush = Sync(bool, True)


class SegmentationEffectLogic(BaseLogic[SegmentationEffectState]):
    update_requested = Signal()

    def __init__(self, server: Server) -> None:
        super().__init__(server, SegmentationEffectState)
        self.paint_erase_effect_prop = PaintEraseEffectProperties(self.server)

        self._segmentation_editor = LabelMapEditor()
        self._brush_model = BrushModel(BrushShape.Sphere)
        self._paint_effects = []

        self.bind_changes({self.name.active_effect: self._update_active_effect})
        self.paint_erase_effect_prop.watch(("brush_size",), self._update_brush_size)
        self.paint_erase_effect_prop.watch(("use_sphere_brush",), self._update_use_sphere_brush)

    def _update_active_effect(self, active_effect: SegmentationEffectType):
        if active_effect == SegmentationEffectType.UNDEFINED:
            self.data.active_effect_prop_id = None
            for effect in self._paint_effects:
                effect.disable_brush()
        elif not self._segmentation_editor.active_segment:
            self.deactivate_effects()
        else:
            self.data.active_effect_prop_id = self.paint_erase_effect_prop._id

            if active_effect == SegmentationEffectType.PAINT:
                self._segmentation_editor.operation = LabelMapOperation.Set
            elif active_effect == SegmentationEffectType.ERASE:
                self._segmentation_editor.operation = LabelMapOperation.Erase

            for effect in self._paint_effects:
                effect.enable_brush()

    def _update_brush_size(self, brush_size: float) -> None:
        if self._brush_model.shape == BrushShape.Cylinder:
            self._brush_model.set_cylinder_parameters(brush_size, 32, 1)
        else:
            self._brush_model.set_sphere_parameters(brush_size, 32, 32)

    def _update_use_sphere_brush(self, use_sphere_brush: bool) -> None:
        self._brush_model.shape = BrushShape.Sphere if use_sphere_brush else BrushShape.Cylinder

    def set_paint_effects(self, slice_views: list[SliceViewLogic]) -> None:
        if not self._paint_effects:  # FIXME: needed to add this to not recreate SegmentPaintEffect2D
            for view in slice_views:
                paint_effect = SegmentPaintEffect2D(
                    view.volume_handler.get_reslice_image_viewer(), self._segmentation_editor, self._brush_model
                )
                self._paint_effects.append(paint_effect)
                paint_effect.update_requested.connect(self.update_requested)

    def set_active_segment(self, object_data: vtkImageData | None, segment_value: int) -> None:
        if object_data is None:
            self.deactivate_effects()
        self._segmentation_editor.labelmap = object_data
        self._segmentation_editor.active_segment = segment_value

    def clear_segment(self, object_data: vtkImageData, segment_value: int):
        self._segmentation_editor.clear_segment(object_data, segment_value)

    def deactivate_effects(self):
        self.data.active_effect = SegmentationEffectType.UNDEFINED
