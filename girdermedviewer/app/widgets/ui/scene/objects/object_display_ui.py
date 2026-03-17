from trame.widgets import html
from trame.widgets import vuetify3 as v3
from trame_dataclass.v2 import Provider

from ....utils import Button, SceneObjectType, Text
from .object_components import PresetSelector, PropertyRangeSlider
from .object_display_opacity_ui import ObjectDisplayOpacityUI


class VolumeDisplayUI(html.Div):
    def __init__(self, obj_display: str, disabled: str, has_opacity: str, threed_presets: str, **kwargs):
        super().__init__(
            **kwargs,
        )
        self.display = obj_display
        self.disabled = disabled
        self.has_opacity = has_opacity
        self.threed_presets = threed_presets
        self._build_ui()

    def _build_ui(self) -> None:
        with self:
            with html.Div(v_if=(f"{self.display}.threed_preset",)):
                Text("Preset 3D", classes="text-subtitle-2 pt-2")
                PresetSelector(
                    v_model=(f"{self.display}.threed_preset.name"),
                    disabled=(self.disabled,),
                    items=(self.threed_presets,),
                )

                Text("Volume Rendering Shift", classes="text-subtitle-2 pt-2")
                PropertyRangeSlider(
                    v_model=(f"{self.display}.threed_preset.vr_shift",),
                    disabled=(self.disabled,),
                    range_min_max=f"{self.display}.scalar_range",
                )

            Text("Window / level", classes="text-subtitle-2 pt-2")
            with (
                PropertyRangeSlider(
                    v_model=f"{self.display}.window_level",
                    disabled=(self.disabled,),
                    range_min_max=f"{self.display}.scalar_range",
                ),
                v3.Template(v_slot_append=True),
            ):
                Button(
                    click=f"{self.display}.window_level = {self.display}.scalar_range",
                    disabled=(self.disabled,),
                    tooltip="Auto Window/Level",
                    icon="mdi-refresh-auto",
                )

            ObjectDisplayOpacityUI(
                v_if=(self.has_opacity,),
                obj_opacity=f"{self.display}.opacity",
            )


class MeshDisplayUI(html.Div):
    def __init__(self, obj_display: str, **kwargs):
        super().__init__(
            **kwargs,
        )
        self.display = obj_display
        self._build_ui()

    def _build_ui(self) -> None:
        with self:
            Text("Color", classes="text-subtitle-2")
            v3.VColorPicker(
                v_model=(f"{self.display}.color",),
                elevation=0,
                modes=("['rgb']",),
                style="width: 100%",
            )

            ObjectDisplayOpacityUI(obj_opacity="display.opacity")


class SceneObjectDisplayUI(html.Div):
    def __init__(self, obj: str, disabled: str, has_opacity: str, threed_presets: str, **kwargs):
        super().__init__(
            **kwargs,
        )
        self.obj = obj

        with self, Provider(name="display", instance=(f"{self.obj}.display",)):
            VolumeDisplayUI(
                obj_display="display",
                disabled=disabled,
                has_opacity=has_opacity,
                threed_presets=threed_presets,
                v_if=(self._is_object_type(SceneObjectType.VOLUME),),
            )
            MeshDisplayUI(
                obj_display="display",
                v_if=(self._is_object_type(SceneObjectType.MESH),),
            )

    def _is_object_type(self, object_type: SceneObjectType) -> str:
        return f"{self.obj}.object_type == '{object_type.value}'"
