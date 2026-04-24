import logging
from collections import defaultdict
from typing import Any

from vtkmodules.vtkCommonDataModel import vtkPolyData
from vtkmodules.vtkRenderingCore import vtkRenderer

from ....utils import (
    ColorPresetParser,
    DataArray,
    get_image_data,
    remove_prop,
    render_mesh_in_3D,
    render_mesh_in_slice,
    set_mesh_opacity,
    set_mesh_solid_color,
    set_mesh_visibility,
)

logger = logging.getLogger(__name__)


class ObjectHandler:
    def __init__(self) -> None:
        self.object_data = defaultdict(list)
        self.renderer: vtkRenderer | None = None

    def set_renderer(self, renderer: vtkRenderer) -> None:
        self.renderer = renderer

    def register_data(self, data_id: str, data: Any) -> None:
        self.object_data[data_id].append(data)

    def unregister_data(self, data_id, only_data=None, remove=True):
        for obj in list(self.object_data.get(data_id, [])):
            if only_data is None or obj == only_data:
                if remove:
                    remove_prop(self.renderer, obj)
                self.object_data[data_id].remove(obj)
        if len(list(self.object_data.get(data_id, []))) == 0:
            self.object_data.pop(data_id)

    def get_data(self, data_id):
        data = self.object_data.get(data_id, [])
        return data[0] if len(data) else None

    def get_actors(self, data_id):
        data = [self.object_data[data_id]] if data_id in self.object_data else self.object_data.values()
        return [obj for objs in data for obj in objs if obj.IsA("vtkActor")]

    def get_image_data(self, data_id):
        data = [self.object_data[data_id]] if data_id in self.object_data else self.object_data.values()
        image_data = [get_image_data(obj) for objs in data for obj in objs if get_image_data(obj) is not None]
        return image_data[0] if len(image_data) > 0 else None

    def get_glyph_actors(self, data_id):
        data = [self.object_data[data_id]] if data_id in self.object_data else self.object_data.values()
        return [obj for objs in data for obj in objs if hasattr(obj, 'GetMapper') and obj.GetMapper().IsA("vtkGlyph3DMapper")]


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
