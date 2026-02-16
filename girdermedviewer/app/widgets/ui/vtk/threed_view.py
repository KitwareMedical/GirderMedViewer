import logging

from girdermedviewer.app.widgets.utils.scene_utils import VolumeLayer

from ...utils import (
    render_mesh_in_3D,
    render_volume_in_3D,
    reset_3D,
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
        # TODO Julien
        if modified:
            self.update()
