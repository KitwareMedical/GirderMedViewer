from trame.widgets import html
from trame.widgets import vuetify3 as v3
from trame_dataclass.v2 import Provider

from ....utils import SceneObjectType
from .object_display_color_ui import (
    MeshDisplayColorUI,
    VolumeDisplayNormalColorUI,
    VolumeDisplayThreeDColorUI,
    VolumeDisplayTwoDColorUI,
)
from .object_display_opacity_ui import ObjectDisplayOpacityUI


class VolumeDisplayUI(html.Div):
    def __init__(self, obj_display: str, disabled: str, has_opacity: str, twod_presets: str, threed_presets: str, **kwargs):
        super().__init__(
            **kwargs,
        )
        self.display = obj_display
        self.disabled = disabled
        self.has_opacity = has_opacity
        self.twod_presets = twod_presets
        self.threed_presets = threed_presets
        self._build_ui()

    def _build_ui(self) -> None:
        with self:
            with html.Div(v_if=(f"{self.display}.number_of_components == 1",)):
                VolumeDisplayThreeDColorUI(self.display, self.threed_presets)
                v3.VDivider(classes="display-property-divider")
                VolumeDisplayTwoDColorUI(self.display, self.twod_presets)
            with html.Div(v_if=(f"{self.display}.number_of_components == 3",)):
                VolumeDisplayNormalColorUI(self.display)
            with html.Div(v_if=(self.has_opacity,),):
                v3.VDivider(classes="display-property-divider")
                ObjectDisplayOpacityUI(obj_opacity=f"{self.display}.opacity")


class MeshDisplayUI(html.Div):
    def __init__(self, obj_display: str, scalar_presets: str, **kwargs):
        super().__init__(
            **kwargs,
        )
        self.display = obj_display
        self.scalar_presets = scalar_presets
        self._build_ui()

    def _build_ui(self) -> None:
        with self:
            MeshDisplayColorUI(self.display, self.scalar_presets)
            v3.VDivider(classes="display-property-divider")
            ObjectDisplayOpacityUI(obj_opacity=f"{self.display}.opacity")


class SceneObjectDisplayUI(html.Div):
    def __init__(self, obj: str, disabled: str, has_opacity: str, color_presets: str, volume_presets: str, **kwargs):
        super().__init__(
            **kwargs,
        )
        self.obj = obj

        with self, Provider(name="display", instance=(f"{self.obj}.display",)):
            VolumeDisplayUI(
                obj_display="display",
                disabled=disabled,
                has_opacity=has_opacity,
                twod_presets=color_presets,
                threed_presets=volume_presets,
                v_if=(self._is_object_type(SceneObjectType.VOLUME),),
            )
            MeshDisplayUI(
                obj_display="display",
                scalar_presets=color_presets,
                v_if=(self._is_object_type(SceneObjectType.MESH),),
            )

    def _is_object_type(self, object_type: SceneObjectType) -> str:
        return f"{self.obj}.object_type == '{object_type.value}'"
