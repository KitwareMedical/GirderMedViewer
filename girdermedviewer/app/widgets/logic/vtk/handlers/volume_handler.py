import logging
from abc import ABC, abstractmethod
from typing import Any

from vtk import (
    vtkImageData,
    vtkImageSlice,
    vtkRenderer,
    vtkResliceImageViewer,
)

from ....utils import (
    ColorPresetParser,
    PresetParser,
    VolumePresetParser,
    convert_color_hex_to_normalized_rgb,
    render_labelmap_as_overlay_in_slice,
    render_volume_as_overlay_in_slice,
    render_volume_as_vector_field,
    render_volume_in_3D,
    render_volume_in_slice,
    set_actor_opacity,
    set_actor_visibility,
    set_reslice_visibility,
    set_reslice_window_level,
    set_slice_opacity,
    set_slice_visibility,
    set_slice_window_level,
    set_vector_field_arrow_length,
    set_vector_field_arrow_thickness,
    set_vector_field_sampling,
    set_volume_visibility,
)
from ....utils.vtk.segmentation import set_segment_color, set_segment_visibility
from ...scene.filters.segmentation_filter_logic import SegmentDisplay
from ...scene.objects.volume_object_logic import VolumeDisplay
from .object_handler import ObjectHandler

logger = logging.getLogger(__name__)


class VolumeHandler(ObjectHandler, ABC):
    def __init__(self, preset_parser: PresetParser, renderer: vtkRenderer):
        super().__init__(renderer)
        self.preset_parser = preset_parser

    @abstractmethod
    def update_volume_visibility(self, data_id: str, data_display: VolumeDisplay) -> bool:
        pass

    @abstractmethod
    def update_volume_normal_color(self, data_id: str, data_display: VolumeDisplay) -> bool:
        pass


class VolumeSliceHandler(VolumeHandler):
    def __init__(self, preset_parser: ColorPresetParser, renderer: vtkRenderer, orientation: int) -> None:
        super().__init__(preset_parser, renderer)
        self.orientation = orientation

    def _is_primary_volume(self, data_id: str) -> bool:
        data = self.get_data(data_id)
        return isinstance(data, vtkResliceImageViewer)

    def _is_secondary_volume(self, data_id: str) -> bool:
        data = self.get_data(data_id)
        return isinstance(data, vtkImageSlice)

    def _has_multiple_primary_volumes(self) -> bool:
        return len([data_id for data_id in self.object_data if self._is_primary_volume(data_id)]) > 1

    def _init_glyph_actors(self, data_id: str) -> None:
        glyph_actor = render_volume_as_vector_field(self.get_image_data(data_id), self.renderer, self.orientation)
        self.register_data(data_id, glyph_actor)

    def has_primary_volume(self) -> bool:
        return self.get_reslice_image_viewer() is not None

    def has_secondary_volume(self) -> bool:
        return len(self.get_image_slices()) > 0

    def unregister_data(self, data_id: str, only_data: Any) -> None:
        # Do no remove ResliceImageViewer if there is still primary volumes
        remove_prop = not (self._is_primary_volume(data_id) and self._has_multiple_primary_volumes())
        super().unregister_data(data_id, only_data, remove_prop)

    def apply_data_display(self, data_id: str, data_display: VolumeDisplay) -> None:
        self.update_volume_window_level(data_id, data_display)

        self.update_volume_opacity(data_id, data_display)

        self.update_volume_scalar_color_preset(data_id, data_display)

        if data_display.normal_color is not None:
            if not self.get_glyph_actors(data_id):
                self._init_glyph_actors(data_id)
            self.update_volume_normal_color(data_id, data_display)
        else:
            self.update_volume_visibility(data_id, data_display)

    def add_primary_volume(self, data_id: str, image_data: vtkImageData) -> None:
        reslice_image_viewer = render_volume_in_slice(image_data, self.renderer, self.orientation)
        self.register_data(data_id, reslice_image_viewer)

    def add_secondary_volume(self, data_id: str, image_data: vtkImageData):
        actor = render_volume_as_overlay_in_slice(image_data, self.renderer, axis=self.orientation)
        self.register_data(data_id, actor)

    def add_labelmap(self, data_id: str, image_data: vtkImageData):
        actor = render_labelmap_as_overlay_in_slice(image_data, axis=self.orientation)
        self.register_data(data_id, actor)

    def update_volume_visibility(self, data_id: str, data_display: VolumeDisplay) -> bool:
        logger.debug(f"set_volume_visibility({data_id}): {data_display.is_visible}")
        normal_color = data_display.normal_color
        show_arrows = data_display.is_visible and normal_color is not None and normal_color.show_arrows
        show_volume = data_display.is_visible and not show_arrows

        modified = False
        reslice_image_viewer = self.get_reslice_image_viewer(data_id)
        if reslice_image_viewer is not None:
            modified = set_reslice_visibility(reslice_image_viewer, show_volume)
        for slice in self.get_image_slices(data_id):
            modified = set_slice_visibility(slice, show_volume) or modified
        for glyph_actor in self.get_glyph_actors(data_id):
            modified = set_actor_visibility(glyph_actor, show_arrows) or modified

        return modified

    def update_volume_opacity(self, data_id: str, data_display: VolumeDisplay) -> bool:
        logger.debug(f"set_volume_opacity({data_id}): {data_display.opacity}")
        modified = False
        # Do not set opacity for reslice image viewer
        for slice in self.get_image_slices(data_id):
            modified = set_slice_opacity(slice, data_display.opacity) or modified
        for glyph_actor in self.get_glyph_actors(data_id):
            modified = set_actor_opacity(glyph_actor, data_display.opacity) or modified
        return modified

    def update_volume_window_level(self, data_id: str, data_display: VolumeDisplay) -> bool:
        if not data_display.window_level:
            return False
        window_level = (
            data_display.window_level[1] - data_display.window_level[0],
            (data_display.window_level[0] + data_display.window_level[1]) / 2,
        )

        logger.debug(f"set_volume_window_level({data_id}): {window_level}")
        modified = False
        reslice_image_viewer = self.get_reslice_image_viewer(data_id)
        if reslice_image_viewer is not None:
            modified = set_reslice_window_level(reslice_image_viewer, window_level)
        for slice in self.get_image_slices(data_id):
            modified = set_slice_window_level(slice, window_level) or modified
        return modified

    def update_volume_scalar_color_preset(self, data_id: str, data_display: VolumeDisplay) -> bool:
        twod_color = data_display.twod_color
        volume = self.get_data(data_id)
        if volume is None or twod_color is None:
            return False

        logger.debug(
            f"set_volume_scalar_color_preset({data_id}):{' Inverse' if twod_color.is_inverted else ''} {twod_color.name}"
        )
        preset = self.preset_parser.get_preset_by_name(twod_color.name)
        if preset is None:
            return False

        modified = False
        reslice_image_viewer = self.get_reslice_image_viewer(data_id)
        if reslice_image_viewer is not None or preset is None:
            modified = self.preset_parser.apply_preset_to_volume(reslice_image_viewer, preset, twod_color.is_inverted)
        for slice in self.get_image_slices(data_id):
            modified = self.preset_parser.apply_preset_to_volume(slice.GetProperty(), preset, twod_color.is_inverted)
        return modified

    def update_volume_normal_color(self, data_id: str, data_display: VolumeDisplay) -> bool:
        normal_color = data_display.normal_color
        if normal_color is None:
            return False

        logger.debug(f"set_volume_normal_color({data_id})")
        modified = self.update_volume_visibility(data_id, data_display)
        for glyph_actor in self.get_glyph_actors(data_id):
            modified = set_vector_field_sampling(glyph_actor, normal_color.sampling, self.orientation) or modified
            modified = set_vector_field_arrow_length(glyph_actor, normal_color.arrow_length) or modified
            modified = set_vector_field_arrow_thickness(glyph_actor, normal_color.arrow_width) or modified

        return modified

    def get_reslice_image_viewer(self, data_id=None) -> vtkResliceImageViewer | None:
        """
        Return the primary volume image viewer if any.
        :param data_id if provided returns only if it matches data_id.
        """
        ids = [data_id] if data_id in self.object_data else self.object_data.keys()
        data = [self.get_data(id) for id in ids if self._is_primary_volume(id)]
        return data[0] if len(data) > 0 else None

    def get_image_slices(self, data_id=None) -> list[vtkImageSlice]:
        ids = [data_id] if data_id in self.object_data else self.object_data.keys()
        return [self.get_data(id) for id in ids if self._is_secondary_volume(id)]

    def update_segment_color(self, data_id: str, segment_id: int, segment_display: SegmentDisplay) -> bool:
        color_tuple = convert_color_hex_to_normalized_rgb(segment_display.color)
        modified = False
        for image_slice in self.get_image_slices(data_id):
            modified = set_segment_color(image_slice, segment_id, color_tuple) or modified
        return modified

    def update_segment_visibility(self, data_id: str, segment_id: int, segment_display: SegmentDisplay) -> bool:
        modified = False
        for image_slice in self.get_image_slices(data_id):
            modified = set_segment_visibility(image_slice, segment_id, segment_display.is_visible) or modified
        return modified


class VolumeThreeDHandler(VolumeHandler):
    def __init__(self, preset_parser: VolumePresetParser, renderer: vtkRenderer) -> None:
        super().__init__(preset_parser, renderer)

    def _init_glyph_actors(self, data_id: str) -> None:
        glyph_actor = render_volume_as_vector_field(self.get_image_data(data_id), self.renderer)
        self.register_data(data_id, glyph_actor)

    def add_volume(self, data_id: str, image_data: vtkImageData) -> None:
        volume = render_volume_in_3D(image_data, self.renderer)
        self.register_data(data_id, volume)

    def apply_data_display(self, data_id: str, data_display: VolumeDisplay) -> None:
        if data_display.normal_color is not None:
            if not self.get_glyph_actors(data_id):
                self._init_glyph_actors(data_id)
            self.update_volume_normal_color(data_id, data_display)
        else:
            self.update_volume_preset(data_id, data_display)
            self.update_volume_visibility(data_id, data_display)

    def update_volume_visibility(self, data_id: str, data_display: VolumeDisplay) -> bool:
        volume = self.get_data(data_id)
        if volume is None:
            return False
        
        visible = data_display.is_visible and data_display.is_threed_visible
        show_arrows = visible and data_display.normal_color and data_display.normal_color.show_arrows
        show_volume = visible and data_display.normal_color is None

        logger.debug(f"set_volume_visibility({data_id}): {show_arrows or show_volume}")
        modified = set_volume_visibility(volume, show_volume)
        
        for glyph_actor in self.get_glyph_actors(data_id):
            modified = set_actor_visibility(glyph_actor, show_arrows) or modified
        return modified

    def update_volume_preset(self, data_id: str, data_display: VolumeDisplay) -> bool:
        threed_color = data_display.threed_color
        volume = self.get_data(data_id)
        if volume is None or threed_color is None:
            return False

        logger.debug(f"set_volume_preset({data_id}): {threed_color.name}, {threed_color.vr_shift}")
        preset = self.preset_parser.get_preset_by_name(threed_color.name)
        if preset is None:
            return False
        return self.preset_parser.apply_preset(volume.GetProperty(), preset, threed_color.vr_shift)

    def update_volume_normal_color(self, data_id: str, data_display: VolumeDisplay) -> bool:
        normal_color = data_display.normal_color
        if normal_color is None:
            return False

        logger.debug(f"set_volume_normal_color({data_id})")
        modified = self.update_volume_visibility(data_id, data_display)
        for glyph_actor in self.get_glyph_actors(data_id):
            modified = set_vector_field_sampling(glyph_actor, normal_color.sampling) or modified
            modified = set_vector_field_arrow_length(glyph_actor, normal_color.arrow_length) or modified
            modified = set_vector_field_arrow_thickness(glyph_actor, normal_color.arrow_width) or modified

        return modified
