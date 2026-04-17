import logging

from trame_dataclass.v2 import get_instance
from trame_server.core import Server

from ....utils import (
    SceneObjectSubtype,
    debounce,
    supported_volume_extensions,
)
from ...vtk.views_logic import ViewsLogic
from ..filters.segmentation_filter_logic import (
    SegmentationFilterLogic,
    SegmentProperties,
)
from .object_handler import ObjectHandler

logger = logging.getLogger(__name__)


class SegmentationDisplayHandler:
    def __init__(self, views_logic: ViewsLogic):
        self.views_logic = views_logic

    def update_opacity(self, labelmap_id: str):
        @debounce(0.05)
        def _update_opacity(opacity: float) -> None:
            if opacity < 0:
                return
            for view in self.views_logic.slice_views:
                modified = view.volume_handler.set_volume_opacity(labelmap_id, opacity)
                if modified:
                    view.update()

        return _update_opacity

    def update_visibility(self, labelmap_id: str):
        def _update_visibility(visible: bool):
            for view in self.views_logic.views:
                modified = view.volume_handler.set_volume_visibility(labelmap_id, visible)
                if modified:
                    view.update()

        return _update_visibility

    def update_segment_color(self, labelmap_id: str, segment_id: int):
        def _update_segment_color(color: str) -> None:
            for view in self.views_logic.slice_views:
                view.volume_handler.set_segment_color(labelmap_id, segment_id, color)

        return _update_segment_color

    def update_segment_visibility(self, labelmap_id: str, segment_id: int):
        def _update_segment_visbility(visible: bool) -> None:
            for view in self.views_logic.slice_views:
                view.volume_handler.set_segment_visibility(labelmap_id, segment_id, visible)

        return _update_segment_visbility


class SegmentationHandler(ObjectHandler):
    def __init__(self, server: Server, views_logic: ViewsLogic):
        super().__init__(server, views_logic)
        self.display_handler = SegmentationDisplayHandler(views_logic)

    @property
    def supported_extensions(self) -> tuple[str]:
        return supported_volume_extensions()

    @staticmethod
    def _get_segment_from_id(segment_id: str) -> SegmentProperties:
        segment: SegmentProperties = get_instance(segment_id)
        return segment

    def add_object_to_views(self, seg_filter_logic: SegmentationFilterLogic):
        self.object_logics[seg_filter_logic._id] = seg_filter_logic
        self._connect_labelmap_to_display_handler(seg_filter_logic)

        self.views_logic.add_volume(
            seg_filter_logic._id,
            seg_filter_logic.object_data,
            seg_filter_logic.display,
            seg_filter_logic.layer,
            SceneObjectSubtype.LABELMAP,
        )

    def remove_object_from_views(self, seg_filter_logic: SegmentationFilterLogic) -> None:
        self.unregister_object_from_views(seg_filter_logic)

    def unregister_object_from_views(self, seg_filter_logic: SegmentationFilterLogic) -> None:
        seg_filter_logic.display.clear_watchers()
        self.object_logics.pop(seg_filter_logic._id)

        self.views_logic.remove_volume(seg_filter_logic._id)

        if self.data.active_labelmap_id == seg_filter_logic._id:
            self.select_segment_in_labelmap(None)

    def set_object_visibility(self, seg_filter_logic: SegmentationFilterLogic, visible: bool) -> None:
        seg_filter_logic.scene_object.is_visible = visible

    def _connect_labelmap_to_display_handler(self, seg_filter_logic: SegmentationFilterLogic):
        seg_filter_logic.display.watch(("opacity",), self.display_handler.update_opacity(seg_filter_logic._id))
        seg_filter_logic.scene_object.watch(
            ("is_visible",), self.display_handler.update_visibility(seg_filter_logic._id)
        )

    def select_segment_in_labelmap(
        self, seg_filter_logic: SegmentationFilterLogic | None, segment_id: str | None = None
    ) -> None:
        if seg_filter_logic is not None and len(seg_filter_logic.segments) > 0:
            if segment_id is None:
                segment_id = seg_filter_logic.segments[-1]._id
                segment_value = seg_filter_logic.segments[-1].value
            else:
                segment_value = SegmentationHandler._get_segment_from_id(segment_id).value

            self.data.active_segment_id = segment_id
            self.data.active_labelmap_id = seg_filter_logic._id
            self.views_logic.segmentation_logic.set_active_segment(seg_filter_logic.object_data, segment_value)
        else:
            self.data.active_segment_id = None
            self.data.active_labelmap_id = None
            self.views_logic.segmentation_logic.set_active_segment(None, 0)

    def add_segment_to_labelmap(self, seg_filter_logic: SegmentationFilterLogic) -> None:
        new_segment = seg_filter_logic.create_segment()
        new_segment.watch(
            ("color",), self.display_handler.update_segment_color(seg_filter_logic._id, new_segment.value)
        )
        new_segment.watch(
            ("is_visible",), self.display_handler.update_segment_visibility(seg_filter_logic._id, new_segment.value)
        )
        self.select_segment_in_labelmap(seg_filter_logic)

    def delete_segment_from_labelmap(self, seg_filter_logic: SegmentationFilterLogic, deleted_segment_id: str) -> None:
        deleted_segment = SegmentationHandler._get_segment_from_id(deleted_segment_id)
        deleted_segment.clear_watchers()
        self.views_logic.segmentation_logic.clear_segment(seg_filter_logic.object_data, deleted_segment.value)
        self.views_logic.update_slice_views()
        seg_filter_logic.delete_segment(deleted_segment_id)

        if deleted_segment_id == self.data.active_segment_id:
            self.select_segment_in_labelmap(seg_filter_logic)
