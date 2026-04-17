import logging

from trame_dataclass.v2 import (
    FieldEncoder,
    StateDataModel,
    Sync,
    TypeValidation,
)

from ....utils import (
    SceneObjectType,
    VolumeLayer,
    VolumeObjectType,
    load_volume,
)
from .scene_object_logic import SceneObjectLogic, ThreeDColor, TwoDColor

logger = logging.getLogger(__name__)


class NormalColor(StateDataModel):
    show_arrows = Sync(bool, False)
    arrow_length = Sync(float, 0.3, type_checking=TypeValidation.SKIP)
    arrow_width = Sync(float, 0.03, type_checking=TypeValidation.SKIP)


class VolumeDisplay(StateDataModel):
    volume_type = Sync(
        VolumeObjectType,
        VolumeObjectType.UNDEFINED,
        convert=FieldEncoder(encoder=VolumeObjectType.encoder, decoder=VolumeObjectType.decoder),
    )
    scalar_range = Sync(list[float])
    window_level = Sync(list[float])
    threed_color = Sync(ThreeDColor, has_dataclass=True)
    twod_color = Sync(TwoDColor, has_dataclass=True)
    normal_color = Sync(NormalColor, has_dataclass=True)
    opacity = Sync(float, 1.0, type_checking=TypeValidation.SKIP)


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
        self.volume_type: VolumeObjectType | None = None


class VolumeObjectLogic(BaseVolumeObjectLogic):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.scene_object.object_type = SceneObjectType.VOLUME
        self.display.threed_color = ThreeDColor(self.server)
        self.display.twod_color = TwoDColor(self.server)
        self.display.normal_color = NormalColor(self.server)
        self.scalar_range: list[float] = []

    def _init_display_properties(self):
        if self.object_data is not None:
            # Init volume type
            self.display.volume_type = (
                VolumeObjectType.VECTOR
                if self.object_data.GetPointData().GetScalars().GetNumberOfComponents() > 1
                else VolumeObjectType.SCALAR
            )

            self.scalar_range = list(self.object_data.GetScalarRange())
            # Init window level
            self.display.scalar_range = self.scalar_range
            # Init window level
            self.display.window_level = self.scalar_range
            # Init 3D preset range
            self.display.threed_color.vr_shift = self.scalar_range

    def load_object_data(self, file_path: str) -> None:
        self.object_data = load_volume(file_path)
        self._init_display_properties()

    def window_level_changed_in_view(self, window_level_in_view: list[float]) -> None:
        window_level_value = [
            window_level_in_view[1] - window_level_in_view[0] / 2,
            window_level_in_view[1] + window_level_in_view[0] / 2,
        ]
        self.display.window_level = window_level_value
