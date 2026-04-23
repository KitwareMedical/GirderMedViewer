import logging
from typing import Any

from vtk import (
    vtkDiscretizableColorTransferFunction,
    vtkImageData,
    vtkImageSlice,
    vtkPiecewiseFunction,
    vtkResliceImageViewer,
)

from ....utils import (
    ColorPresetParser,
    VolumePresetParser,
    render_labelmap_as_overlay_in_slice,
    render_volume_as_overlay_in_slice,
    render_volume_as_vector_field,
    render_volume_in_3D,
    render_volume_in_slice,
    set_actor_opacity,
    set_actor_visibility,
    set_reslice_opacity,
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
from ...scene.objects.volume_object_logic import VolumeDisplay
from .object_handler import ObjectHandler

logger = logging.getLogger(__name__)


class VolumeSliceHandler(ObjectHandler):
    def __init__(self, preset_parser: ColorPresetParser) -> None:
        super().__init__()
        self.preset_parser = preset_parser

    def _is_primary_volume(self, data_id: str) -> bool:
        data = self.get_data(data_id)
        return isinstance(data, vtkResliceImageViewer)

    def _is_secondary_volume(self, data_id: str) -> bool:
        data = self.get_data(data_id)
        return isinstance(data, vtkImageSlice)

    def _has_multiple_primary_volumes(self) -> bool:
        return len([data_id for data_id in self.object_data if self._is_primary_volume(data_id)]) > 1

    def has_primary_volume(self) -> bool:
        return self.get_reslice_image_viewer() is not None

    def has_secondary_volume(self) -> bool:
        return len(self.get_image_slices()) > 0

    def unregister_data(self, data_id: str, only_data: Any) -> None:
        # Do no remove ResliceImageViewer if there is still primary volumes
        remove_prop = not (self._is_primary_volume(data_id) and self._has_multiple_primary_volumes())
        super().unregister_data(data_id, only_data, remove_prop)

    def apply_volume_display_properties(
        self, data_id: str, display_property: VolumeDisplay, orientation: int, is_primary: bool
    ) -> None:
        self.set_volume_window_level_min_max(data_id, display_property.window_level)
        if not is_primary:
            self.set_volume_opacity(data_id, display_property.opacity)
        elif display_property.twod_color is not None:
            self.set_volume_scalar_color_preset(
                data_id,
                display_property.twod_color.name,
                display_property.twod_color.is_inverted,
            )
        elif display_property.normal_color is not None:
            self.set_volume_normal_color(
                data_id,
                display_property.normal_color.show_arrows,
                display_property.normal_color.sampling,
                display_property.normal_color.arrow_length,
                display_property.normal_color.arrow_width,
                orientation,
            )

    def add_primary_volume(self, data_id: str, image_data: vtkImageData, orientation: int) -> None:
        reslice_image_viewer = render_volume_in_slice(image_data, self.renderer, orientation)
        self.register_data(data_id, reslice_image_viewer)

    def add_secondary_volume(self, data_id: str, image_data: vtkImageData, orientation: int):
        actor = render_volume_as_overlay_in_slice(image_data, self.renderer, axis=orientation)
        self.register_data(data_id, actor)

    def add_labelmap(self, data_id: str, image_data: vtkImageData, orientation: int):
        actor = render_labelmap_as_overlay_in_slice(image_data, axis=orientation)
        self.register_data(data_id, actor)

    def set_volume_visibility(self, data_id: str, visible: bool) -> bool:
        logger.debug(f"set_volume_visibility({data_id}): {visible}")
        modified = False
        reslice_image_viewer = self.get_reslice_image_viewer(data_id)
        if reslice_image_viewer is not None:
            modified = set_reslice_visibility(reslice_image_viewer, visible)
        for slice in self.get_image_slices(data_id):
            modified = set_slice_visibility(slice, visible) or modified
        for glyph_actor in self.get_glyph_actors(data_id):
            modified = set_actor_visibility(glyph_actor, visible) or modified
        return modified

    def set_volume_opacity(self, data_id: str, opacity: float) -> bool:
        logger.debug(f"set_volume_opacity({data_id}): {opacity}")
        modified = False
        reslice_image_viewer = self.get_reslice_image_viewer(data_id)
        if reslice_image_viewer is not None:
            modified = set_reslice_opacity(reslice_image_viewer, opacity)
        for slice in self.get_image_slices(data_id):
            modified = set_slice_opacity(slice, opacity) or modified
        for glyph_actor in self.get_glyph_actors(data_id):
            modified = set_actor_opacity(glyph_actor, opacity) or modified
        return modified

    def set_volume_window_level(self, data_id: str, window_level: tuple[float]) -> bool:
        logger.debug(f"set_volume_window_level({data_id}): {window_level}")
        modified = False
        reslice_image_viewer = self.get_reslice_image_viewer(data_id)
        if reslice_image_viewer is not None:
            modified = set_reslice_window_level(reslice_image_viewer, window_level)
        for slice in self.get_image_slices(data_id):
            modified = set_slice_window_level(slice, window_level) or modified
        return modified

    def set_volume_window_level_min_max(self, data_id: str, window_level_min_max: list[float]) -> bool:
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
        show_arrows: bool,
        sampling: int,
        arrow_length: float,
        arrow_width: float,
        orientation: int,
    ) -> bool:
        logger.debug(f"set_volume_normal_color({data_id})")
        modified = False
        glyph_actors = self.get_glyph_actors(data_id)
        if show_arrows and len(glyph_actors) == 0:
            glyph_actor = render_volume_as_vector_field(self.get_image_data(data_id), self.renderer, orientation)
            self.register_data(data_id, glyph_actor)
            glyph_actors = [glyph_actor]
            modified = True
        for glyph_actor in glyph_actors:
            modified = set_actor_visibility(glyph_actor, show_arrows) or modified
            modified = set_vector_field_sampling(glyph_actor, orientation, sampling) or modified
            modified = set_vector_field_arrow_length(glyph_actor, arrow_length) or modified
            modified = set_vector_field_arrow_thickness(glyph_actor, arrow_width) or modified
        for image_slice in self.get_image_slices(data_id):
            modified = set_actor_visibility(image_slice, not show_arrows) or modified
        reslice_image_viewer = self.get_reslice_image_viewer(data_id)
        if reslice_image_viewer is not None:
            modified = set_actor_visibility(reslice_image_viewer, not show_arrows) or modified
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

    def set_segment_color(self, data_id: str, segment_id: int, color: str) -> None:
        # color format: #rrggbb
        color_value = [
            int(color[1:3], base=16) / 255.0,
            int(color[3:5], base=16) / 255.0,
            int(color[5:7], base=16) / 255.0,
        ]
        for image_slice in self.get_image_slices(data_id):
            lut: vtkDiscretizableColorTransferFunction = image_slice.GetProperty().GetLookupTable()
            value = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
            lut.GetNodeValue(segment_id, value)
            value[1:4] = color_value
            lut.SetNodeValue(segment_id, value)

    def set_segment_visibility(self, data_id: str, segment_id: int, visible: bool) -> None:
        for image_slice in self.get_image_slices(data_id):
            lut: vtkDiscretizableColorTransferFunction = image_slice.GetProperty().GetLookupTable()
            of: vtkPiecewiseFunction = lut.GetScalarOpacityFunction()
            value = [0.0, 0.0, 0.0, 0.0]
            of.GetNodeValue(segment_id, value)
            value[1] = float(visible)
            of.SetNodeValue(segment_id, value)


class VolumeThreeDHandler(ObjectHandler):
    def __init__(self, preset_parser: VolumePresetParser) -> None:
        super().__init__()
        self.preset_parser = preset_parser

    def apply_volume_display_properties(self, data_id: str, display_property: VolumeDisplay) -> None:
        if display_property.threed_color is not None:
            self.set_volume_preset(
                data_id,
                display_property.threed_color.name,
                display_property.threed_color.vr_shift,
            )
        elif display_property.normal_color is not None:
            self.set_volume_normal_color(
                data_id,
                display_property.normal_color.show_arrows,
                display_property.normal_color.sampling,
                display_property.normal_color.arrow_length,
                display_property.normal_color.arrow_width,
            )

    def add_volume(self, data_id: str, image_data: vtkImageData) -> None:
        volume = render_volume_in_3D(image_data, self.renderer)
        self.register_data(data_id, volume)

    def set_volume_visibility(self, data_id: str, visible: bool) -> bool:
        logger.debug(f"set_volume_visibility({data_id}): {visible}")
        volume = self.get_data(data_id)
        if volume is None:
            return False
        return set_volume_visibility(volume, visible)

    def set_volume_preset(self, data_id: str, preset_name: str, range: list[float]) -> bool:
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
        sampling: int,
        arrow_length: float,
        arrow_width: float,
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
            modified = set_vector_field_sampling(glyph_actor, None, sampling) or modified
            modified = set_vector_field_arrow_length(glyph_actor, arrow_length) or modified
            modified = set_vector_field_arrow_thickness(glyph_actor, arrow_width) or modified

        return set_volume_visibility(volume, not show_arrows) or modified
