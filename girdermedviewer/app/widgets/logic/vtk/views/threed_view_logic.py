import logging

from ....utils import (
    VolumeLayer,
    reset_3D,
)
from ..handlers.volume_handler import VolumeThreeDHandler
from ..place_roi_logic import PlaceROILogic
from .view_logic import ViewLogic

logger = logging.getLogger(__name__)


class ThreeDViewLogic(ViewLogic):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.volume_handler = VolumeThreeDHandler(self.volume_preset_parser)

    def add_volume(self, data_id, image_data, layer: VolumeLayer, _is_labelmap: bool):
        if layer == VolumeLayer.PRIMARY:
            self.volume_handler.add_volume(data_id, image_data)

    def add_mesh(self, data_id, poly_data):
        self.mesh_handler.add_mesh_in_3D(data_id, poly_data)

    def init_roi(self, roi: PlaceROILogic):
        roi.box_widget.SetInteractor(self.renderer.GetRenderWindow().GetInteractor())
        roi.box_widget.SetCurrentRenderer(self.renderer)

    def reset(self):
        reset_3D(self.renderer)
        self.update()
