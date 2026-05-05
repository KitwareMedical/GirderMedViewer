from trame.widgets import html
from trame.widgets import vuetify3 as v3

from ....utils import SceneObjectSubtype, SceneObjectType
from .object_display_color_ui import (
    MeshDisplayColorUI,
    VolumeDisplayNormalColorUI,
    VolumeDisplayThreeDColorUI,
    VolumeDisplayTwoDColorUI,
)
from .object_display_opacity_ui import ObjectDisplayOpacityUI


class VolumeDisplayUI(html.Div):
    def __init__(
        self,
        obj_display: str,
        obj_subtype: str,
        is_primary: str,
        twod_presets: str,
        threed_presets: str,
        **kwargs,
    ):
        super().__init__(
            **kwargs,
        )
        self.display = obj_display
        self.subtype = obj_subtype
        self.is_primary = is_primary
        self.twod_presets = twod_presets
        self.threed_presets = threed_presets
        self._build_ui()

    def _build_ui(self) -> None:
        with self:
            with html.Div(v_if=(self._is_volume_subtype(SceneObjectSubtype.SCALAR),)):
                VolumeDisplayThreeDColorUI(
                    v_if=(f"{self.display}.threed_color",),
                    obj_display=self.display,
                    threed_presets=self.threed_presets,
                )
                v3.VDivider(classes="display-property-divider")
                VolumeDisplayTwoDColorUI(
                    v_if=(f"{self.display}.twod_color",), obj_display=self.display, twod_presets=self.twod_presets
                )

            with html.Div(v_if=(self._is_volume_subtype(SceneObjectSubtype.VECTOR),)):
                VolumeDisplayNormalColorUI(v_if=(f"{self.display}.normal_color",), obj_display=self.display)

            with html.Div(
                v_if=(f"!{self.is_primary}",),
            ):
                v3.VDivider(
                    v_if=(f"!{self._is_volume_subtype(SceneObjectSubtype.LABELMAP)}",),
                    classes="display-property-divider",
                )
                ObjectDisplayOpacityUI(obj_opacity=f"{self.display}.opacity")

    def _is_volume_subtype(self, subtype: SceneObjectSubtype) -> str:
        return f"({self.subtype} === '{subtype.value}')"


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
    def __init__(self, obj: str, obj_display: str, is_primary: str, color_presets: str, volume_presets: str, **kwargs):
        super().__init__(**kwargs)
        self.obj = obj

        with self:
            VolumeDisplayUI(
                obj_display=obj_display,
                obj_subtype=f"{self.obj}.object_subtype",
                is_primary=is_primary,
                twod_presets=color_presets,
                threed_presets=volume_presets,
                v_if=(self._is_object_type(SceneObjectType.VOLUME),),
            )
            MeshDisplayUI(
                obj_display=obj_display,
                scalar_presets=color_presets,
                v_if=(self._is_object_type(SceneObjectType.MESH),),
            )

    def _is_object_type(self, object_type: SceneObjectType) -> str:
        return f"({self.obj}.object_type == '{object_type.value}')"
