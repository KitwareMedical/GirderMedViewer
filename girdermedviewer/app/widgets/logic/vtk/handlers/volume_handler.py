import logging
from typing import Any

from vtk import vtkImageData, vtkImageSlice, vtkResliceImageViewer

from ....utils import (
    ColorPresetParser,
    VolumePresetParser,
    render_volume_as_overlay_in_slice,
    render_volume_as_vector_field,
    render_volume_in_3D,
    render_volume_in_slice,
    set_actor_visibility,
    set_reslice_opacity,
    set_reslice_visibility,
    set_reslice_window_level,
    set_slice_opacity,
    set_slice_visibility,
    set_slice_window_level,
    set_vector_field_arrow_length,
    set_vector_field_arrow_thickness,
    set_volume_visibility,
)
from .mesh_handler import ObjectHandler

logger = logging.getLogger(__name__)


class VolumeTwoDHandler(ObjectHandler):
    def __init__(self, preset_parser: ColorPresetParser):
        super().__init__()
        self.preset_parser = preset_parser

    def _is_primary_volume(self, data_id):
        data = self.get_data(data_id)
        return isinstance(data, vtkResliceImageViewer)

    def _is_secondary_volume(self, data_id):
        data = self.get_data(data_id)
        return isinstance(data, vtkImageSlice)

    def _has_multiple_primary_volumes(self):
        return len([data_id for data_id in self.object_data if self._is_primary_volume(data_id)]) > 1

    def has_primary_volume(self):
        return self.get_reslice_image_viewer() is not None

    def has_secondary_volume(self):
        return len(self.get_image_slices()) > 0

    def unregister_data(self, data_id: str, only_data: Any) -> None:
        # Do no remove ResliceImageViewer if there is still primary volumes
        remove_prop = not (self._is_primary_volume(data_id) and self._has_multiple_primary_volumes())
        super().unregister_data(data_id, only_data, remove_prop)

    def add_primary_volume(self, data_id, image_data: vtkImageData, orientation, obliques: bool):
        reslice_image_viewer = render_volume_in_slice(image_data, self.renderer, orientation.value, obliques=obliques)
        self.register_data(data_id, reslice_image_viewer)

    def add_secondary_volume(self, data_id, image_data, orientation):
        actor = render_volume_as_overlay_in_slice(image_data, self.renderer, orientation.value)
        self.register_data(data_id, actor)

    def set_volume_visibility(self, data_id: str, visible: bool) -> bool:
        logger.debug(f"set_volume_visibility({data_id}): {visible}")
        modified = False
        reslice_image_viewer = self.get_reslice_image_viewer(data_id)
        if reslice_image_viewer is not None:
            modified = set_reslice_visibility(reslice_image_viewer, visible)
        for slice in self.get_image_slices(data_id):
            modified = set_slice_visibility(slice, visible) or modified
        return modified

    def set_volume_opacity(self, data_id, opacity) -> bool:
        logger.debug(f"set_volume_opacity({data_id}): {opacity}")
        modified = False
        reslice_image_viewer = self.get_reslice_image_viewer(data_id)
        if reslice_image_viewer is not None:
            modified = set_reslice_opacity(reslice_image_viewer, opacity)
        for slice in self.get_image_slices(data_id):
            modified = set_slice_opacity(slice, opacity) or modified
        return modified

    def set_volume_window_level(self, data_id, window_level) -> bool:
        logger.debug(f"set_volume_window_level({data_id}): {window_level}")
        modified = False
        reslice_image_viewer = self.get_reslice_image_viewer(data_id)
        if reslice_image_viewer is not None:
            modified = set_reslice_window_level(reslice_image_viewer, window_level)
        for slice in self.get_image_slices(data_id):
            modified = set_slice_window_level(slice, window_level) or modified
        return modified

    def set_volume_window_level_min_max(self, data_id, window_level_min_max) -> bool:
        """
        :see-also set_volume_window_level
        """
        if window_level_min_max is not None:
            window = window_level_min_max[1] - window_level_min_max[0]
            level = (window_level_min_max[0] + window_level_min_max[1]) / 2
            return self.set_volume_window_level(data_id, (window, level))
        return False

    def set_volume_scalar_color_preset(self, data_id: str, preset_name: str, is_inverted: bool) -> bool:
        logger.debug(f"set_volume_scalar_color_preset({data_id}):{' Inverse' if is_inverted else ''} {preset_name}")
        preset = self.preset_parser.get_preset_by_name(preset_name)
        if preset is None:
            return False

        modified = False
        reslice_image_viewer = self.get_reslice_image_viewer(data_id)
        if reslice_image_viewer is not None or preset is None:
            modified = self.preset_parser.apply_preset_to_volume(reslice_image_viewer, preset, is_inverted)
        for slice in self.get_image_slices(data_id):
            modified = self.preset_parser.apply_preset_to_volume(slice.GetProperty(), preset, is_inverted)
        return modified

    def set_volume_normal_color(
        self,
        data_id: str,
        _show_arrows: bool,
        _arrow_length: bool,
        _arrow_width: bool,
    ) -> bool:
        logger.debug(f"set_volume_normal_color({data_id})")
        modified = False
        glyph_actors = self.get_glyph_actors(data_id)
        if _show_arrows and len(glyph_actors) == 0:
            glyph_actor = render_volume_as_vector_field(
                self.get_image_data(data_id), self.renderer, self.orientation.value
            )
            self.register_data(data_id, glyph_actor)
            glyph_actors = [glyph_actor]
            modified = True
        # FIXME: add a convenient function to set visibility of any actor
        for glyph_actor in glyph_actors:
            modified = set_actor_visibility(glyph_actor, _show_arrows) or modified
            modified = set_vector_field_arrow_length(glyph_actor, _arrow_length) or modified
            modified = set_vector_field_arrow_thickness(glyph_actor, _arrow_width) or modified
        for image_slice in self.get_image_slices(data_id):
            modified = set_actor_visibility(image_slice, not _show_arrows) or modified
        reslice_image_viewer = self.get_reslice_image_viewer(data_id)
        if reslice_image_viewer is not None:
            modified = set_actor_visibility(reslice_image_viewer, not _show_arrows) or modified
        return modified

    def get_reslice_image_viewer(self, data_id=None):
        """
        Return the primary volume image viewer if any.
        :param data_id if provided returns only if it matches data_id.
        """
        ids = [data_id] if data_id in self.object_data else self.object_data.keys()
        data = [self.get_data(id) for id in ids if self._is_primary_volume(id)]
        return data[0] if len(data) > 0 else None

    def get_image_slices(self, data_id=None):
        ids = [data_id] if data_id in self.object_data else self.object_data.keys()
        return [self.get_data(id) for id in ids if self._is_secondary_volume(id)]


class VolumeThreeDHandler(ObjectHandler):
    def __init__(self, preset_parser: VolumePresetParser):
        super().__init__()
        self.preset_parser = preset_parser

    def add_volume(self, data_id: str, image_data: vtkImageData) -> None:
        volume = render_volume_in_3D(image_data, self.renderer)
        self.register_data(data_id, volume)

    def set_volume_visibility(self, data_id: str, visible: bool) -> bool:
        logger.debug(f"set_volume_visibility({data_id}): {visible}")
        volume = self.get_data(data_id)
        if volume is None:
            return False
        return set_volume_visibility(volume, visible)

    def set_volume_preset(self, data_id, preset_name, range) -> bool:
        volume = self.get_data(data_id)
        if volume is None:
            return False
        logger.debug(f"set_volume_preset({data_id}): {preset_name}, {range}")
        preset = self.preset_parser.get_preset_by_name(preset_name)
        if preset is None:
            return False
        return self.preset_parser.apply_preset(volume.GetProperty(), preset, range)

    def set_volume_normal_color(
        self,
        data_id: str,
        show_arrows: bool,
        arrow_length: bool,
        arrow_width: bool,
    ) -> bool:
        volume = self.get_data(data_id)
        if volume is None:
            return False
        logger.debug(f"set_volume_normal_color({data_id})")
        modified = False
        glyph_actors = self.get_glyph_actors(data_id)
        if show_arrows and len(glyph_actors) == 0:
            glyph_actor = render_volume_as_vector_field(self.get_image_data(data_id), self.renderer)
            self.register_data(data_id, glyph_actor)
            glyph_actors = [glyph_actor]
            modified = True
        # FIXME: add a convenient function to set visibility of any actor
        for glyph_actor in glyph_actors:
            modified = set_actor_visibility(glyph_actor, show_arrows) or modified
            modified = set_vector_field_arrow_length(glyph_actor, arrow_length) or modified
            modified = set_vector_field_arrow_thickness(glyph_actor, arrow_width) or modified

        return set_volume_visibility(volume, not show_arrows) or modified
