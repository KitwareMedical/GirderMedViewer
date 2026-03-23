import logging

from girdermedviewer.app.widgets.utils.scene_utils import VolumeLayer

from ...utils import (
    render_mesh_in_3D,
    render_volume_in_3D,
    render_volume_as_vector_field,
    reset_3D,
    set_actor_visibility,
    set_vector_field_arrow_length,
    set_vector_field_arrow_thickness,
    set_volume_visibility,
)
from .base_view import ViewType, VtkView

logger = logging.getLogger(__name__)


class ThreeDView(VtkView):
    def __init__(self, ref, **kwargs):
        super().__init__(ref=ref, view_type=ViewType.THREED, **kwargs)
        self._build_ui()

    def add_volume(self, data_id, image_data, _layer: VolumeLayer):
        volume = render_volume_in_3D(image_data, self.renderer)
        self.register_data(data_id, volume)
        self.update()

    def add_mesh(self, data_id, poly_data):
        actor = render_mesh_in_3D(poly_data, self.renderer)
        self.register_data(data_id, actor)
        self.update()

    def reset(self):
        reset_3D(self.renderer)
        self.update()

    def set_volume_visibility(self, data_id: str, visible: bool) -> None:
        logger.debug(f"set_volume_visibility({data_id}): {visible}")
        volume = self.get_data(data_id)
        if volume is None:
            return
        modified = set_volume_visibility(volume, visible)
        if modified:
            self.update()

    def set_volume_preset(self, data_id, preset_name, range):
        if self.volume_preset_parser is None:
            return
        logger.debug(f"set_volume_preset({data_id}): {preset_name}, {range}")
        preset = self.volume_preset_parser.get_preset_by_name(preset_name)
        if preset is None:
            return
        volume = self.get_data(data_id)
        if volume is None:
            return
        modified = self.volume_preset_parser.apply_preset(volume.GetProperty(), preset, range)
        if modified:
            self.update()

    def set_volume_normal_color(
        self,
        data_id: str,
        _show_arrows: bool,
        _arrow_length: bool,
        _arrow_width: bool,
    ):
        logger.debug(f"set_volume_normal_color({data_id})")
        modified = False
        glyph_actors = self.get_glyph_actors(data_id)
        if _show_arrows and len(glyph_actors) == 0:
            glyph_actor = render_volume_as_vector_field(
                self.get_image_data(data_id),
                self.renderer
            )
            self.register_data(data_id, glyph_actor)
            glyph_actors = [glyph_actor]
            modified = True
        # FIXME: add a convenient function to set visibility of any actor
        for glyph_actor in glyph_actors:
            modified = set_actor_visibility(glyph_actor, _show_arrows) or modified
            modified = set_vector_field_arrow_length(glyph_actor, _arrow_length) or modified
            modified = set_vector_field_arrow_thickness(glyph_actor, _arrow_width) or modified
        volume = self.get_data(data_id)
        if volume is not None:
            modified = set_volume_visibility(volume, not _show_arrows) or modified
        if modified:
            self.update()
