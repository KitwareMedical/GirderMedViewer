import logging

from trame_dataclass.v2 import get_instance
from vtk import vtkPolyData, vtkRenderer

from ....utils import (
    ColorPresetParser,
    DataArray,
    MeshColoringMode,
    convert_color_hex_to_normalized_rgb,
    render_mesh_in_3D,
    render_mesh_in_slice,
    set_mesh_opacity,
    set_mesh_solid_color,
    set_mesh_visibility,
)
from ...scene.objects.mesh_object_logic import MeshDisplay
from .object_handler import ObjectHandler

logger = logging.getLogger(__name__)


class MeshHandler(ObjectHandler):
    def __init__(self, preset_parser: ColorPresetParser, renderer: vtkRenderer) -> None:
        super().__init__(renderer)
        self.preset_parser = preset_parser

    def apply_mesh_display_properties(self, data_id: str, display_properties: MeshDisplay) -> None:
        self.register_display(data_id, display_properties)

        # Set opacity
        self.set_mesh_opacity(data_id, display_properties.opacity)

        # Set color
        active_array = get_instance(display_properties.active_array_id)
        assert isinstance(active_array, DataArray)
        if active_array.coloring_mode == MeshColoringMode.SOLID:
            self.set_mesh_solid_color(data_id, display_properties.solid_color)

        elif active_array.coloring_mode == MeshColoringMode.ARRAY:
            self.set_mesh_array_color(
                data_id,
                active_array,
                display_properties.array_color.name,
                display_properties.array_color.is_inverted,
                display_properties.array_color.array_range,
            )

        # Set visibility
        self.set_mesh_visibility(data_id, display_properties.is_visible)

    def add_mesh_in_3D(self, data_id: str, poly_data: vtkPolyData) -> None:
        actor = render_mesh_in_3D(poly_data, self.renderer)
        self.register_data(data_id, actor)

    def add_mesh_in_slice(self, data_id: str, poly_data: vtkPolyData, orientation: int) -> None:
        actor = render_mesh_in_slice(poly_data, orientation, self.renderer)
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

    def set_mesh_solid_color(self, data_id: str, color: str) -> bool:
        color_tuple = convert_color_hex_to_normalized_rgb(color)
        modified = False
        for actor in self.get_actors(data_id):
            modified = set_mesh_solid_color(actor, color_tuple) or modified
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

    def has_mesh(self) -> bool:
        return len(list(self.object_data)) > 0
