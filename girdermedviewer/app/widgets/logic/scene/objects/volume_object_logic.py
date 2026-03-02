import logging

from trame_dataclass.v2 import (
    StateDataModel,
    Sync,
    TypeValidation,
)

from ....utils import (
    SceneObjectType,
    debounce,
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
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.scene_object.object_type = SceneObjectType.VOLUME
        self.display = VolumeDisplay(
            self.server,
            threed_preset=VolumePreset(self.server),
        )
        self.scene_object.display = self.display._id

        self.volume_range: list[float] = []

        self.display.watch(("opacity",), self._update_opacity)
        self.display.watch(("window_level",), self._update_window_level)
        self.display.threed_preset.watch(("name", "vr_shift"), self._update_threed_preset)

    @debounce(0.05)
    def _update_opacity(self, opacity: float) -> None:
        if opacity < 0:
            return
        for view in self.twod_views:
            view.set_volume_opacity(self.scene_object._id, opacity)

    @debounce(0.05)
    def _update_window_level(self, window_level: list[float]) -> None:
        for view in self.twod_views:
            view.set_volume_window_level_min_max(self.scene_object._id, window_level)
            view.update()

    @debounce(0.05)
    def _update_threed_preset(self, volume_preset_name: str, volume_preset_vr_shift: list[float]) -> None:
        for view in self.threed_views:
            view.set_volume_preset(
                self.scene_object._id,
                volume_preset_name,
                volume_preset_vr_shift,
            )

    def _load(self) -> None:
        if self.object_data is not None:
            self.load_to_view()
            self.volume_range = list(self.object_data.GetScalarRange())

            # Init window level
            self.display.scalar_range = self.volume_range

            # Init window level
            self.display.window_level = self.volume_range

            # Init 3D preset range
            self.display.threed_preset.vr_shift = self.volume_range

            self.scene_object.gui.loading = False

    def load(self, file_path: str) -> None:
        self.object_data = load_volume(file_path)
        self._load()

    def window_level_changed_in_view(self, window_level_in_view: list[float]) -> None:
        window_level_value = [
            window_level_in_view[1] - window_level_in_view[0] / 2,
            window_level_in_view[1] + window_level_in_view[0] / 2,
        ]
        self.display.window_level = window_level_value
