import logging

from trame_dataclass.v2 import (
    StateDataModel,
    Sync,
    TypeValidation,
)

from ....utils import (
    SceneObjectType,
    VolumePriorityType,
    load_volume,
)
from .scene_object_logic import SceneObjectLogic

logger = logging.getLogger(__name__)

DEFAULT_VOLUME_PRESET_NAME = "CT-Cardiac3"


class VolumePreset(StateDataModel):
    name = Sync(str, DEFAULT_VOLUME_PRESET_NAME)
    vr_shift = Sync(list[float], list)


class VolumeDisplay(StateDataModel):
    scalar_range = Sync(list[float], list)
    window_level = Sync(list[float], list)
    threed_preset = Sync(VolumePreset, has_dataclass=True)
    opacity = Sync(float, 1.0, type_checking=TypeValidation.SKIP)


class VolumeObjectLogic(SceneObjectLogic):
    volume_range: list[float] = list
    priority: VolumePriorityType = VolumePriorityType.UNDEFINED

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.scene_object.object_type = SceneObjectType.VOLUME
        self.display = VolumeDisplay(
            self.server,
            threed_preset=VolumePreset(self.server),
        )
        self.scene_object.display = self.display._id

    def _init_display_properties(self):
        if self.object_data is not None:
            self.volume_range = list(self.object_data.GetScalarRange())

            # Init window level
            self.display.scalar_range = self.volume_range

            # Init window level
            self.display.window_level = self.volume_range

            # Init 3D preset range
            self.display.threed_preset.vr_shift = self.volume_range

    def load_object_data(self, file_path: str) -> None:
        self.object_data = load_volume(file_path)
        self._init_display_properties()

    def window_level_changed_in_view(self, window_level_in_view: list[float]) -> None:
        window_level_value = [
            window_level_in_view[1] - window_level_in_view[0] / 2,
            window_level_in_view[1] + window_level_in_view[0] / 2,
        ]
        self.display.window_level = window_level_value
