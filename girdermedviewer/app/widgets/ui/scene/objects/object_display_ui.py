from trame.widgets import html
from trame.widgets import vuetify3 as v3

from ....utils import Button, SceneObjectType, Text


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
            Text("Preset 3D", classes="text-subtitle-2 pt-2")
            (
                PresetSelector(
                    items=(self.threed_presets,),
                    v_model=(f"{self.display}.threed_preset.name"),
                ),
            )

            Text("Preset 2D", classes="text-subtitle-2 pt-2")
            with (
                PresetSelector(
                    items=(self.twod_presets,),
                    v_model=(f"{self.display}.twod_preset.name"),
                ),
                v3.Template(v_slot_append=True),
            ):
                v3.VCheckbox(
                    v_model=(f"{self.display}.twod_preset.is_inverted",),
                    label="Invert",
                    hide_details=True,
                )

            Text("Volume Rendering Shift", classes="text-subtitle-2 pt-2")
            PropertyRangeSlider(
                range_min_max=f"{self.display}.scalar_range", v_model=(f"{self.display}.threed_preset.vr_shift",)
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

            with html.Div(v_if=(f"{self.display}.opacity > 0",)):
                Text("Opacity", classes="text-subtitle-2 pt-2")
                OpacitySlider(v_model=(f"{self.display}.opacity",))


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
            Text("Color", classes="text-subtitle-2")
            v3.VColorPicker(
                v_model=(f"{self.display}.color",),
                elevation=0,
                modes=("['rgb']",),
                style="width: 100%",
            )

            Text("Color by scalar", classes="text-subtitle-2 pt-2")
            with (
                v3.VSelect(
                    items=(self.color_presets,),
                    v_model=(f"{self.display}.scalar_preset.name"),
                    variant="solo-filled",
                    flat=True,
                ),
                v3.Template(v_slot_append=True),
            ):
                v3.VCheckbox(
                    v_model=(f"{self.display}.scalar_preset.is_inverted",),
                    label="Invert",
                    hide_details=True,
                )

            Text("Opacity", classes="text-subtitle-2 pt-2")
            OpacitySlider(v_model=(f"{self.display}.opacity",))


class OpacitySlider(v3.VSlider):
    def __init__(self, **kwargs):
        super().__init__(min=0, max=1, step=1e-6, hide_details=True, **kwargs)


class PresetSelector(v3.VSelect):
    def __init__(self, **kwargs):
        super().__init__(variant="solo-filled", flat=True, hide_details=True, **kwargs)
        with self:
            with (
                v3.Template(v_slot_item="{ props }"),
                v3.VListItem(v_bind="props"),
                v3.Template(v_slot_prepend=""),
            ):
                v3.VImg(v_if=("props.data",), src=("props.data",), height=64, width=64, classes="mr-2")

            with v3.Template(v_slot_selection="{item}"):
                v3.VImg(v_if=("item.props.data",), src=("item.props.data",), height=32, width=32, classes="mr-2")
                html.Span("{{ item.title }}")


class PropertyRangeSlider(v3.VRangeSlider):
    def __init__(self, range_min_max: str, **kwargs):
        super().__init__(
            min=(f"{range_min_max}[0]",),
            max=(f"{range_min_max}[1]",),
            step=kwargs.pop("step", 1e-6),
            hide_details=True,
            **kwargs,
        )


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
