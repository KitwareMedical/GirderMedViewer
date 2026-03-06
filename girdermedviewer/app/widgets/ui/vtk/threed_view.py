import logging

from ...utils import (
    render_mesh_in_3D,
    render_volume_in_3D,
    reset_3D,
)
from .base_view import ViewType, VtkView

logger = logging.getLogger(__name__)


class ThreeDView(VtkView):
    def __init__(self, ref, **kwargs):
        super().__init__(ref=ref, view_type=ViewType.THREED, **kwargs)
        self._build_ui()

    def get_volumes(self):
        return [obj for objs in self.data.values() for obj in objs if obj.IsA("vtkVolume")]

    def add_volume(self, image_data, data_id=None):
        volume = render_volume_in_3D(image_data, self.renderer)
        self.register_data(data_id, volume)
        self.update()

    def add_mesh(self, poly_data, data_id=None):
        actor = render_mesh_in_3D(poly_data, self.renderer)
        self.register_data(data_id, actor)
        self.update()

    def reset(self):
        reset_3D(self.renderer)
        self.update()

    def set_volume_preset(self, volume_id, preset_name, range):
        if self.volume_preset_parser is None:
            return
        logger.debug(f"set_volume_preset({volume_id}): {preset_name}, {range}")
        preset = self.volume_preset_parser.get_preset_by_name(preset_name)
        if preset is None:
            return
        volume = self.get_data(volume_id)
        if volume is None:
            return
        modified = self.volume_preset_parser.apply_preset(preset, volume.GetProperty(), range)
        if modified:
            self.update()
