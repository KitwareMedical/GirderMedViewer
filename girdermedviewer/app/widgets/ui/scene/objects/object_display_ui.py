from trame.widgets import html
from trame.widgets import vuetify3 as v3
from trame_dataclass.v2 import Provider
from trame_server.utils.typed_state import TypedState

from ....utils import Button, SceneObjectType, Text
from ..scene_state import SceneState
from .object_components import PresetSelector, PropertyRangeSlider
from .object_display_opacity_ui import ObjectDisplayOpacityUI


class VolumeDisplayUI(html.Div):
    def __init__(self, obj: str, threed_presets: str, **kwargs):
        super().__init__(
            **kwargs,
        )
        self._typed_state = TypedState(self.state, SceneState)
        self.obj = obj
        self.threed_presets = threed_presets
        self._build_ui()

    def _build_ui(self) -> None:
        with self, Provider(name="display", instance=(f"{self.obj}.display",)):
            Text("Preset 3D", classes="text-subtitle-2 pt-2")
            (
                PresetSelector(
                    v_model=("display.threed_preset.name"),
                    items=(self.threed_presets,),
                ),
            )

            Text("Volume Rendering Shift", classes="text-subtitle-2 pt-2")
            PropertyRangeSlider(
                v_model=("display.threed_preset.vr_shift",),
                range_min_max="display.scalar_range",
            )

            Text("Window / level", classes="text-subtitle-2 pt-2")
            with (
                PropertyRangeSlider(
                    v_model="display.window_level",
                    range_min_max="display.scalar_range",
                ),
                v3.Template(v_slot_append=True),
            ):
                Button(
                    tooltip="Auto Window/Level",
                    icon="mdi-refresh-auto",
                    click="display.window_level = display.scalar_range",
                )
            ObjectDisplayOpacityUI(
                v_if=(f"!{self._typed_state.name.primary_volume_ids}.includes({self.obj}._id)",),
                obj_opacity="display.opacity",
            )


class MeshDisplayUI(html.Div):
    def __init__(self, obj: str, **kwargs):
        super().__init__(
            **kwargs,
        )
        self.obj = obj
        self._build_ui()

    def _build_ui(self) -> None:
        with self, Provider(name="display", instance=(f"{self.obj}.display",)):
            Text("Color", classes="text-subtitle-2")
            v3.VColorPicker(
                v_model=("display.color",),
                elevation=0,
                modes=("['rgb']",),
                style="width: 100%",
            )

            ObjectDisplayOpacityUI(obj_opacity="display.opacity")


class SceneObjectDisplayUI(html.Div):
    def __init__(self, obj: str, threed_presets: str, **kwargs):
        super().__init__(
            **kwargs,
        )
        self.obj = obj
        self.type = f"{obj}.object_type"
        self.threed_presets = threed_presets
        self._build_ui()

    def _build_ui(self) -> None:
        with self:
            VolumeDisplayUI(
                obj=self.obj,
                threed_presets=self.threed_presets,
                v_if=(f"{self.type} == '{SceneObjectType.VOLUME.value}'",),
            )
            MeshDisplayUI(
                obj=self.obj,
                v_if=(f"{self.type} == '{SceneObjectType.MESH.value}'",),
            )
