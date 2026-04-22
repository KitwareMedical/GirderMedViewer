import logging

from trame_dataclass.v2 import (
    StateDataModel,
    Sync,
    TypeValidation,
)

from ....utils import (
    SceneObjectSubtype,
    SceneObjectType,
    VolumeLayer,
    load_volume,
)
from .scene_object_logic import SceneObjectLogic, ThreeDColor, TwoDColor

logger = logging.getLogger(__name__)


class NormalColor(StateDataModel):
    show_arrows = Sync(bool, False)
    sampling = Sync(int, 10, type_checking=TypeValidation.SKIP)
    arrow_length = Sync(float, 10, type_checking=TypeValidation.SKIP)
    arrow_width = Sync(float, 0.03, type_checking=TypeValidation.SKIP)


class VolumeDisplay(StateDataModel):
    scalar_range = Sync(list[float])
    window_level = Sync(list[float])
    threed_color = Sync(ThreeDColor, has_dataclass=True)
    twod_color = Sync(TwoDColor, has_dataclass=True)
    normal_color = Sync(NormalColor, has_dataclass=True)
    opacity = Sync(float, 0.5, type_checking=TypeValidation.SKIP)  # Used only for secondary volumes


class BaseVolumeObjectLogic(SceneObjectLogic):
    volume_range: list[float] = list
    layer: VolumeLayer = VolumeLayer.UNDEFINED

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.scene_object.object_type = SceneObjectType.VOLUME
        self.display = VolumeDisplay(
            self.server,
        )
        self.scene_object.display = self.display._id
        self.scene_object.flush()


class VolumeObjectLogic(BaseVolumeObjectLogic):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.scene_object.object_type = SceneObjectType.VOLUME
        self.scalar_range: list[float] = []

    def _init_display_properties(self):
        if self.object_data is not None:
            self.scalar_range = list(self.object_data.GetScalarRange())
            self.display.twod_color = TwoDColor(self.server)
            self.display.threed_color = ThreeDColor(self.server, vr_shift=self.scalar_range)

            # Init volume type
            if self.object_data.GetPointData().GetScalars().GetNumberOfComponents() > 1:
                self.scene_object.object_subtype = SceneObjectSubtype.VECTOR
                self.display.normal_color = NormalColor(self.server)
            else:
                self.scene_object.object_subtype = SceneObjectSubtype.SCALAR

            # Init window level
            self.display.scalar_range = self.scalar_range
            # Init window level
            self.display.window_level = self.scalar_range

    def load_object_data(self, file_path: str) -> None:
        self.object_data = load_volume(file_path)
        self._init_display_properties()

    def window_level_changed_in_view(self, window_level_in_view: list[float]) -> None:
        window_level_value = [
            window_level_in_view[1] - window_level_in_view[0] / 2,
            window_level_in_view[1] + window_level_in_view[0] / 2,
        ]
        self.display.window_level = window_level_value
