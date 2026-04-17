import logging

from vtkmodules.vtkCommonDataModel import vtkPolyData

from ....utils import (
    ColorPresetParser,
    DataArray,
    render_mesh_in_3D,
    render_mesh_in_slice,
    set_mesh_opacity,
    set_mesh_solid_color,
    set_mesh_visibility,
)
from .object_handler import ObjectHandler

logger = logging.getLogger(__name__)


class MeshHandler(ObjectHandler):
    def __init__(self, preset_parser: ColorPresetParser) -> None:
        super().__init__()
        self.preset_parser = preset_parser

    def add_mesh_in_3D(self, data_id: str, poly_data: vtkPolyData) -> None:
        actor = render_mesh_in_3D(poly_data, self.renderer)
        self.register_data(data_id, actor)

    def add_mesh_in_slice(self, data_id, poly_data: vtkPolyData, orientation) -> None:
        actor = render_mesh_in_slice(poly_data, orientation.value, self.renderer)
        self.register_data(data_id, actor)

    def set_mesh_visibility(self, data_id: str, visible: bool) -> bool:
        modified = False
        for actor in self.get_actors(data_id):
            modified = set_mesh_visibility(actor, visible) or modified
        return modified

    def set_mesh_opacity(self, data_id: str, opacity: float) -> bool:
        modified = False
        for actor in self.get_actors(data_id):
            modified = set_mesh_opacity(actor, opacity) or modified
        return modified

    def set_mesh_solid_color(self, data_id, color: str) -> bool:
        modified = False
        for actor in self.get_actors(data_id):
            modified = set_mesh_solid_color(actor, color) or modified
        return modified

    def set_mesh_array_color(
        self, data_id: str, array_obj: DataArray, preset_name: str, is_inverted: bool, preset_range: list[float]
    ) -> bool:
        if self.preset_parser is None:
            return False

        logger.debug(f"set_mesh_array_color({data_id}): {preset_name}")
        preset = self.preset_parser.get_preset_by_name(preset_name)
        if preset is None:
            return False

        modified = False
        for actor in self.get_actors(data_id):
            modified = (
                self.preset_parser.apply_preset_to_mesh(actor, array_obj, preset, preset_range, is_inverted) or modified
            )
        return modified
