from trame.widgets import html
from trame.widgets import vuetify3 as v3

from ....utils import Button, SceneObjectType, Text
from .object_components import PresetSelector, PropertyRangeSlider
from .object_display_opacity_ui import ObjectDisplayOpacityUI


class VolumeDisplayUI(html.Div):
    def __init__(self, obj_display: str, threed_presets: str, **kwargs):
        super().__init__(
            **kwargs,
        )
        self.display = obj_display
        self.threed_presets = threed_presets
        self._build_ui()

    def _build_ui(self) -> None:
        with self:
            Text("Preset 3D", classes="text-subtitle-2 pt-2")
            (
                PresetSelector(
                    items=(self.threed_presets,),
                    v_model=(f"{self.display}.threed_preset.name"),
                ),
            )

            Text("Volume Rendering Shift", classes="text-subtitle-2 pt-2")
            PropertyRangeSlider(
                range_min_max=f"{self.display}.scalar_range",
                v_model=(f"{self.display}.threed_preset.vr_shift",),
            )

            Text("Window / level", classes="text-subtitle-2 pt-2")
            with (
                PropertyRangeSlider(
                    range_min_max=f"{self.display}.scalar_range",
                    v_model=f"{self.display}.window_level",
                ),
                v3.Template(v_slot_append=True),
            ):
                Button(
                    tooltip="Auto Window/Level",
                    icon="mdi-refresh-auto",
                    click=f"{self.display}.window_level = {self.display}.scalar_range",
                )

            ObjectDisplayOpacityUI(v_if=(f"{self.display}.opacity >= 0",), obj_opacity=f"{self.display}.opacity")


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

            ObjectDisplayOpacityUI(obj_opacity=f"{self.display}.opacity")


class SceneObjectDisplayUI(html.Div):
    def __init__(self, obj_display: str, obj_type: str, threed_presets: str, **kwargs):
        super().__init__(
            **kwargs,
        )
        self.display = obj_display
        self.type = obj_type
        self.threed_presets = threed_presets
        self._build_ui()

    def _build_ui(self) -> None:
        with self:
            VolumeDisplayUI(
                obj_display=self.display,
                threed_presets=self.threed_presets,
                v_if=(f"{self.type} == '{SceneObjectType.VOLUME.value}'",),
            )
            MeshDisplayUI(
                obj_display=self.display,
                v_if=(f"{self.type} == '{SceneObjectType.MESH.value}'",),
            )
