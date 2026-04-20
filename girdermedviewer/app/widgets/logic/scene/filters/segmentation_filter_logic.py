from trame_dataclass.v2 import ServerOnly, StateDataModel, Sync
from vtk import VTK_UNSIGNED_CHAR

from ....utils import SceneObjectSubtype, VolumeLayer, get_random_color
from ..objects.volume_object_logic import BaseVolumeObjectLogic, VolumeObjectLogic

MAX_SEGMENTS_PER_LABELMAP = 255


class SegmentProperties(StateDataModel):
    name = Sync(str)
    color = Sync(str)
    value = ServerOnly(int)
    is_color_dialog_visible = Sync(bool, False)
    is_visible = Sync(bool, True)


class SegmentationFilterProperties(StateDataModel):
    is_active = Sync(bool, False)
    segments = Sync(list[SegmentProperties], list, has_dataclass=True)


class SegmentationFilterLogic(BaseVolumeObjectLogic):
    def __init__(
        self,
        original_logic: VolumeObjectLogic,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.scene_object.object_subtype = SceneObjectSubtype.LABELMAP
        self.layer = VolumeLayer.SECONDARY

        self._next_segment_id = 1
        self.scene_object_filter = SegmentationFilterProperties(self.server)
        self.scene_object.filter_prop_id = self.scene_object_filter._id

        self.original_data = original_logic.object_data
        self.load_object_data()

    def load_object_data(self) -> None:
        self.object_data = self.original_data.NewInstance()
        self.object_data.CopyStructure(self.original_data)
        self.object_data.AllocateScalars(VTK_UNSIGNED_CHAR, 1)
        self.object_data.GetPointData().GetScalars().FillComponent(0, 0)

    @property
    def segments(self) -> list[SegmentProperties]:
        return self.scene_object_filter.segments

    def update_next_segment_id(self):
        existing_segment_ids = [segment.value for segment in self.segments]
        self._next_segment_id = next(
            (val for val in range(1, MAX_SEGMENTS_PER_LABELMAP + 1) if val not in existing_segment_ids),
            None,
        )

    def create_segment(self) -> SegmentProperties:
        if self._next_segment_id is None:
            raise ValueError(f"Labelmap cannot exceed {MAX_SEGMENTS_PER_LABELMAP} segments.")

        new_segment = SegmentProperties(
            self.server, name=f"Segment_{self._next_segment_id}", value=self._next_segment_id, color=get_random_color()
        )
        self.scene_object_filter.segments = [*self.segments, new_segment]
        self.update_next_segment_id()
        return new_segment

    def delete_segment(self, deleted_segment_id: str) -> None:
        self.scene_object_filter.segments = [segment for segment in self.segments if segment._id != deleted_segment_id]
        self.update_next_segment_id()
