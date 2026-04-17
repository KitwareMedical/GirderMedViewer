import logging
from collections import defaultdict
from typing import Any

from vtkmodules.vtkRenderingCore import vtkRenderer

from ....utils import (
    get_image_data,
    remove_prop,
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
