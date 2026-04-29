import logging

from vtk import vtkImageData, vtkPolyData

from ....utils import (
    SceneObjectSubtype,
    VolumeLayer,
    reset_3D,
)
from ...scene.objects.mesh_object_logic import MeshDisplay
from ...scene.objects.volume_object_logic import VolumeDisplay
from ..handlers.volume_handler import VolumeThreeDHandler
from .view_logic import ViewLogic

logger = logging.getLogger(__name__)


class ThreeDViewLogic(ViewLogic[VolumeThreeDHandler]):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.volume_handler = VolumeThreeDHandler(self.volume_preset_parser, self.renderer)

    def add_volume(
        self,
        data_id: str,
        image_data: vtkImageData,
        display_properties: VolumeDisplay,
        layer: VolumeLayer,
        subtype: SceneObjectSubtype,
    ) -> None:
        if subtype == SceneObjectSubtype.LABELMAP and layer == VolumeLayer.SECONDARY:
            return
        self.volume_handler.add_volume(data_id, image_data)
        self.volume_handler.apply_volume_display_properties(data_id, display_properties)

    def add_mesh(self, data_id: str, poly_data: vtkPolyData, display_properties: MeshDisplay) -> None:
        self.mesh_handler.add_mesh_in_3D(data_id, poly_data)
        self.mesh_handler.apply_mesh_display_properties(data_id, display_properties)

    def reset(self) -> None:
        reset_3D(self.renderer)
        self.update()
