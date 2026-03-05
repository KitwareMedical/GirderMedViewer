from trame.widgets import html
from trame.widgets import vuetify3 as v3

from ....utils import SceneObjectType, VolumeObjectType
from .object_display_color_ui import (
    MeshDisplayColorUI,
    VolumeDisplayNormalColorUI,
    VolumeDisplayThreeDColorUI,
    VolumeDisplayTwoDColorUI,
)
from .object_display_opacity_ui import ObjectDisplayOpacityUI


class VolumeDisplayUI(html.Div):
    def __init__(self, obj_display: str, twod_presets: str, threed_presets: str, **kwargs):
        super().__init__(
            **kwargs,
        )
        self.display = obj_display
        self.twod_presets = twod_presets
        self.threed_presets = threed_presets
        self._build_ui()

    def _build_ui(self) -> None:
        with self:
            with html.Div(v_if=(self._is_volume_type(VolumeObjectType.SCALAR),)):
                VolumeDisplayThreeDColorUI(self.display, self.threed_presets)
                v3.VDivider(classes="display-property-divider")
                VolumeDisplayTwoDColorUI(self.display, self.twod_presets)

            with html.Div(v_if=(self._is_volume_type(VolumeObjectType.VECTOR),)):
                VolumeDisplayNormalColorUI(self.display)

            with html.Div(v_if=(f"{self.display}.opacity >= 0",)):
                v3.VDivider(
                    v_if=(f"!{self._is_volume_type(VolumeObjectType.LABELMAP)}",), classes="display-property-divider"
                )
                ObjectDisplayOpacityUI(self.display)

    def _is_volume_type(self, volume_type: VolumeObjectType) -> str:
        return f"{self.display}.volume_type === '{volume_type.value}'"


class MeshDisplayUI(html.Div):
    def __init__(self, obj_display: str, color_presets: str, **kwargs):
        super().__init__(
            **kwargs,
        )
        self.display = obj_display
        self.color_presets = color_presets
        self._build_ui()

    def _build_ui(self) -> None:
        with self:
            MeshDisplayColorUI(self.display, self.color_presets)
            v3.VDivider(classes="display-property-divider")
            ObjectDisplayOpacityUI(self.display)


class SceneObjectDisplayUI(html.Div):
    def __init__(self, obj_display: str, obj_type: str, color_preset: str, volume_presets: str, **kwargs):
        super().__init__(
            **kwargs,
        )
        self.display = obj_display
        self.type = obj_type
        self.color_preset = color_preset
        self.volume_presets = volume_presets
        self._build_ui()

    def _build_ui(self) -> None:
        with self:
            VolumeDisplayUI(
                obj_display=self.display,
                twod_presets=self.color_preset,
                threed_presets=self.volume_presets,
                v_if=(f"{self.type} == '{SceneObjectType.VOLUME.value}'",),
            )
            MeshDisplayUI(
                obj_display=self.display,
                color_presets=self.color_preset,
                v_if=(f"{self.type} == '{SceneObjectType.MESH.value}'",),
            )
