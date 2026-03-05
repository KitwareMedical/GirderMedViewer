from trame_dataclass.v2 import FieldEncoder, StateDataModel, Sync
from vtk import VTK_UNSIGNED_CHAR

from ....utils import SegmentationEffectType, get_random_color
from ..objects import LabelmapVolumeObjectLogic, VolumeObjectLogic


class PaintEraseEffectProperties(StateDataModel):
    brush_size = Sync(float, 15)
    use_sphere_brush = Sync(bool, False)


class SegmentProperties(StateDataModel):
    name = Sync(str)
    color = Sync(str)
    is_color_dialog_visible = Sync(bool, False)
    is_visible = Sync(bool, True)


class SegmentationFilterProperties(StateDataModel):
    segments = Sync(list[SegmentProperties], list, has_dataclass=True)
    active_segment_id = Sync(str)
    active_effect = Sync(
        SegmentationEffectType,
        SegmentationEffectType.UNDEFINED,
        convert=FieldEncoder(SegmentationEffectType.encoder, SegmentationEffectType.decoder),
    )
    active_effect_prop_id = Sync(str)


class SegmentationFilterLogic(LabelmapVolumeObjectLogic):
    def __init__(
        self,
        original_logic: VolumeObjectLogic,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.segment_count = 1
        self.scene_object_filter = SegmentationFilterProperties(self.server)
        self.scene_object.filter_prop = self.scene_object_filter._id

        self.paint_erase_effect_prop = PaintEraseEffectProperties(self.server)

        self.original_data = original_logic.object_data
        self._init_object_data()

        self.scene_object_filter.watch(("active_effect",), self._update_active_effect)
        self.paint_erase_effect_prop.watch(("brush_size",), self._update_brush_size)
        self.paint_erase_effect_prop.watch(("use_sphere_brush",), self._update_use_sphere_brush)

    def _init_object_data(self):
        self.object_data = self.original_data.NewInstance()
        self.object_data.CopyStructure(self.original_data)
        self.object_data.AllocateScalars(VTK_UNSIGNED_CHAR, 1)
        self.object_data.GetPointData().GetScalars().FillComponent(0, 0)
        self._load()

    @property
    def segments(self) -> list[SegmentProperties]:
        return self.scene_object_filter.segments

    @property
    def active_segment_id(self) -> str:
        return self.scene_object_filter.active_segment_id

    @property
    def active_effect(self) -> str:
        return self.scene_object_filter.active_effect

    def _update_active_effect(self, active_effect: SegmentationEffectType):
        if active_effect == SegmentationEffectType.PAINT:  # noqa: SIM114
            self.scene_object_filter.active_effect_prop_id = self.paint_erase_effect_prop._id
            # TODO: trigger paintbrush mode

        elif active_effect == SegmentationEffectType.ERASE:
            self.scene_object_filter.active_effect_prop_id = self.paint_erase_effect_prop._id
            # TODO: trigger erase mode

        else:
            self.scene_object_filter.active_effect_prop_id = None

    def _update_brush_size(self, brush_size: float) -> None:
        # TODO
        pass

    def _update_use_sphere_brush(self, use_sphere_brush: bool) -> None:
        # TODO
        pass

    def add_segment(self) -> None:
        new_segment = SegmentProperties(self.server, name=f"Segment_{self.segment_count}", color=get_random_color())
        self.scene_object_filter.segments = [*self.segments, new_segment]
        self.scene_object_filter.active_segment_id = new_segment._id
        self.segment_count += 1

    def delete_segment(self, deleted_segment_id: str) -> None:
        self.scene_object_filter.segments = [segment for segment in self.segments if segment._id != deleted_segment_id]
        if deleted_segment_id == self.active_segment_id:
            self.scene_object_filter.active_segment_id = self.segments[0]._id if len(self.segments) > 0 else None
