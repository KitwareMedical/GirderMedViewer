from trame_dataclass.v2 import ServerOnly, StateDataModel, Sync, get_instance
from vtk import VTK_UNSIGNED_CHAR

from girdermedviewer.app.widgets.utils.scene_utils import VolumeLayer

from ....utils import VolumeObjectType, get_random_color
from ..objects.volume_object_logic import BaseVolumeObjectLogic, VolumeObjectLogic


class SegmentProperties(StateDataModel):
    name = Sync(str)
    color = Sync(str)
    value = ServerOnly(int)
    is_color_dialog_visible = Sync(bool, False)
    is_visible = Sync(bool, True)


class SegmentationFilterProperties(StateDataModel):
    segments = Sync(list[SegmentProperties], list, has_dataclass=True)


class SegmentationFilterLogic(BaseVolumeObjectLogic):
    def __init__(
        self,
        original_logic: VolumeObjectLogic,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.volume_type: VolumeObjectType.LABELMAP
        self.layer = VolumeLayer.SECONDARY

        self.segment_count = 1
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

    def get_segment_value(self, segment_id: str) -> int:
        segment: SegmentProperties = get_instance(segment_id)
        return segment.value

    def create_segment(self) -> SegmentProperties:
        new_segment = SegmentProperties(
            self.server, name=f"Segment_{self.segment_count}", value=self.segment_count, color=get_random_color()
        )
        self.scene_object_filter.segments = [*self.segments, new_segment]
        self.segment_count += 1
        return new_segment

    def delete_segment(self, deleted_segment_id: str) -> None:
        self.scene_object_filter.segments = [segment for segment in self.segments if segment._id != deleted_segment_id]
