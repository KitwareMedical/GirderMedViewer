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
from .scene_object_logic import SceneObjectLogic, ThreeDColor, TwoDColor

logger = logging.getLogger(__name__)


class NormalColor(StateDataModel):
    show_arrows = Sync(bool, False)
    arrow_length = Sync(float, 1.0)
    arrow_width = Sync(float, 1.0)


class VolumeDisplay(StateDataModel):
    scalar_range = Sync(list[float])
    window_level = Sync(list[float])
    number_of_components = Sync(int)
    threed_color = Sync(ThreeDColor, has_dataclass=True)
    twod_color = Sync(TwoDColor, has_dataclass=True)
    normal_color = Sync(NormalColor, has_dataclass=True)
    opacity = Sync(float, 1.0, type_checking=TypeValidation.SKIP)


class VolumeObjectLogic(SceneObjectLogic):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.scene_object.object_type = SceneObjectType.VOLUME
        self.display = VolumeDisplay(
            self.server,
            threed_color=ThreeDColor(self.server),
            twod_color=TwoDColor(self.server),
            normal_color=NormalColor(self.server),
        )
        self.scene_object.display = self.display._id
        self.volume_range: list[float] = []

        self.display.watch(("opacity",), self._update_opacity)
        self.display.watch(("window_level",), self._update_window_level)
        self.display.threed_color.watch(("name", "vr_shift"), self._update_threed_coloring)
        self.display.twod_color.watch(("name", "is_inverted"), self._update_twod_coloring)
        self.display.normal_color.watch(("show_arrows", "arrow_length", "arrow_width"), self._update_normal_coloring)

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
    def _update_threed_coloring(self, preset_name: str, vr_shift: list[float]) -> None:
        for view in self.threed_views:
            view.set_volume_preset(
                self.scene_object._id,
                preset_name,
                vr_shift,
            )

    @debounce(0.05)
    def _update_twod_coloring(self, preset_name: str, is_inverted: bool) -> None:
        for view in self.twod_views:
            view.set_volume_scalar_color_preset(
                self.scene_object._id,
                preset_name,
                is_inverted,
            )

    @debounce(0.05)
    def _update_normal_coloring(self, show_arrows: bool, arrow_length: float, arrow_width: float) -> None:
        for view in self.views:
            view.set_volume_normal_color(
                self.scene_object._id,
                show_arrows,
                arrow_length,
                arrow_width,
            )

    def _load(self) -> None:
        if self.object_data is not None:
            self.volume_range = list(self.object_data.GetScalarRange())

            # Init window level
            self.display.scalar_range = self.volume_range
            self.display.number_of_components = self.object_data.GetPointData().GetScalars().GetNumberOfComponents()

            # Init window level
            self.display.window_level = self.volume_range

            # Init 3D preset range
            self.display.threed_color.vr_shift = self.volume_range

            # TODO provide self.display to views to load proper configuration
            self.load_to_view()

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
