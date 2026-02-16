import logging

from trame_dataclass.v2 import FieldEncoder, StateDataModel, Sync, get_instance
from trame_server import Server

from ...ui import (
    SceneObjectType,
    SliceView,
    ThreeDView,
    VtkView,
)
from ...utils import (
    debounce,
    get_random_color,
    load_mesh,
    load_volume,
)
from ..base_logic import BaseLogic

logger = logging.getLogger(__name__)


class VolumePreset(StateDataModel):
    name = Sync(str, "CT-Cardiac3")
    vr_shift = Sync(list[float], list)


class ColorPreset(StateDataModel):
    name = Sync(str, "Grayscale")
    is_inverted = Sync(bool, False)


class VolumeDisplay(StateDataModel):
    scalar_range = Sync(list[float], list)
    window_level = Sync(list[float], list)
    threed_preset = Sync(VolumePreset, has_dataclass=True)
    twod_preset = Sync(ColorPreset, has_dataclass=True)
    opacity = Sync(float, 1.0)


class MeshDisplay(StateDataModel):
    color = Sync(str)
    scalar_preset = Sync(ColorPreset, has_dataclass=True)
    opacity = Sync(float, 0.8)


class SceneObjectInfo(StateDataModel):
    created = Sync(str)
    updated = Sync(str)
    size = Sync(str)


class SceneObjectMetadata(StateDataModel):
    meta = Sync(dict[str | str] | None)
    parent_meta = Sync(dict[str | str] | None)


class SceneObject(StateDataModel):
    name = Sync(str)
    loading = Sync(bool, True)
    window = Sync(str)
    object_id = Sync(str)
    object_type = Sync(
        SceneObjectType,
        SceneObjectType.UNDEFINED,
        convert=FieldEncoder(SceneObjectType.encoder, SceneObjectType.decoder),
    )
    info = Sync(SceneObjectInfo, has_dataclass=True)
    metadata = Sync(SceneObjectMetadata, has_dataclass=True)
    mesh_display = Sync(MeshDisplay, has_dataclass=True)
    volume_display = Sync(VolumeDisplay, has_dataclass=True)


class SceneObjectLogic(BaseLogic[None]):
    def __init__(
        self,
        server: Server,
        scene_object: SceneObject,
        views: list[VtkView],
    ) -> None:
        super().__init__(server, None)
        self.scene = get_instance(self.state.scene_id)
        self.scene_object = scene_object
        self.image_data = None
        self.views = views
        self.set_views(views)

    @property
    def twod_views(self) -> list[SliceView]:
        return [view for view in self.views if isinstance(view, SliceView)]

    @property
    def threed_views(self) -> list[ThreeDView]:
        return [view for view in self.views if isinstance(view, ThreeDView)]

    def is_volume(self) -> bool:
        return self.scene_object.object_type == SceneObjectType.VOLUME

    def is_mesh(self) -> bool:
        return self.scene_object.object_type == SceneObjectType.MESH

    def _add_to_view(self, view: VtkView) -> None:
        assert self.image_data is not None
        adder = getattr(view, f"add_{self.scene_object.object_type.value}")
        if adder is not None:
            adder(self.image_data, self.scene_object.object_id)

    def _remove_from_view(self, view: VtkView) -> None:
        remover = getattr(view, f"remove_{self.scene_object.object_type.value}")
        if remover is not None:
            remover(self.scene_object.object_id)

    def load_to_view(self) -> None:
        for view in self.views:
            self._add_to_view(view)

    def set_views(self, views: list[VtkView]) -> None:
        for view in self.views:
            if view not in views:
                self._remove_from_view(view)
        if self.image_data is not None:
            for view in views:
                if view not in self.views:
                    self._add_to_view(view)
        self.views = views


class VolumeObjectLogic(SceneObjectLogic):
    def __init__(self, server: Server, scene_object: SceneObject, views: list[VtkView]) -> None:
        super().__init__(server, scene_object, views)
        self.scene_object.object_type = SceneObjectType.VOLUME
        self.scene_object.volume_display = VolumeDisplay(
            self.server,
            threed_preset=VolumePreset(self.server),
            twod_preset=ColorPreset(self.server),
        )

        self.volume_range: list[float] = []

        self.scene_object.volume_display.watch(("opacity",), self._update_opacity)
        self.scene_object.volume_display.watch(("window_level",), self._update_window_level)
        self.scene_object.volume_display.threed_preset.watch(("name", "vr_shift"), self._update_threed_preset)
        self.scene_object.volume_display.twod_preset.watch(("name", "is_inverted"), self._update_twod_preset)

    @debounce(0.05)
    def _update_opacity(self, opacity: float) -> None:
        if opacity < 0:
            return
        for view in self.twod_views:
            view.set_volume_opacity(self.scene_object.object_id, opacity)

    @debounce(0.05)
    def _update_window_level(self, window_level: list[float]) -> None:
        for view in self.twod_views:
            view.set_volume_window_level_min_max(self.scene_object.object_id, window_level)
            view.update()

    @debounce(0.05)
    def _update_threed_preset(self, volume_preset_name: str, volume_preset_vr_shift: list[float]) -> None:
        for view in self.threed_views:
            view.set_volume_preset(
                self.scene_object.object_id,
                volume_preset_name,
                volume_preset_vr_shift,
            )

    @debounce(0.05)
    def _update_twod_preset(self, twod_preset_name: str, twod_preset_is_inverted: bool) -> None:
        for view in self.twod_views:
            view.set_volume_scalar_color_preset(
                self.scene_object.object_id,
                twod_preset_name,
                twod_preset_is_inverted,
            )

    def load(self, file_path: str) -> None:
        self.image_data = load_volume(file_path)
        if self.image_data is not None:
            self.load_to_view()
            self.volume_range = list(self.image_data.GetScalarRange())

            # Init window level
            self.scene_object.volume_display.scalar_range = self.volume_range

            # Init window level
            self.scene_object.volume_display.window_level = self.volume_range

            # Init 3D preset range
            self.scene_object.volume_display.threed_preset.vr_shift = self.volume_range

            self.scene_object.loading = False

    def window_level_changed_in_view(self, window_level_in_view: list[float]) -> None:
        window_level_value = [
            window_level_in_view[1] - window_level_in_view[0] / 2,
            window_level_in_view[1] + window_level_in_view[0] / 2,
        ]
        self.scene_object.volume_display.window_level = window_level_value


class MeshObjectLogic(SceneObjectLogic):
    def __init__(self, server: Server, scene_object: SceneObject, views: list[VtkView]) -> None:
        super().__init__(server, scene_object, views)
        self.scene_object.object_type = SceneObjectType.MESH
        self.scene_object.mesh_display = MeshDisplay(
            self.server,
            color=get_random_color(),
            opacity=0.8,
        )

        self.scene_object.mesh_display.watch(("opacity",), self._update_opacity)
        self.scene_object.mesh_display.watch(("color",), self._update_color)
        self.scene_object.mesh_display.scalar_preset.watch(("name", "is_inverted"), self._update_scalar_preset)

    @debounce(0.05)
    def _update_opacity(self, opacity: float) -> None:
        for view in self.views:
            view.set_mesh_opacity(self.scene_object.object_id, opacity)

    @debounce(0.05)
    def _update_color(self, color: str) -> None:
        hex = color.lstrip("#")
        color_tuple = tuple(float(int(hex[i : i + 2], 16)) / 255.0 for i in (0, 2, 4))
        for view in self.views:
            view.set_mesh_color(self.scene_object.object_id, color_tuple)

    @debounce(0.05)
    def _update_scalar_preset(self, color_preset_name: str, color_preset_is_inverted: bool) -> None:
        for view in self.views:
            view.set_mesh_scalar_color_preset(self.scene_object.object_id, color_preset_name, color_preset_is_inverted)

    def load(self, file_path: str) -> None:
        self.image_data = load_mesh(file_path)
        self.load_to_view()

        self.scene_object.loading = False
