from trame.widgets import html
from trame.widgets import vuetify3 as v3
from trame_dataclass.v2 import Provider

from ....utils import (
    Button,
    ColorPicker,
    MeshColoringMode,
    NumberInput,
    RangeSlider,
    Selector,
    Text,
)


class PresetSelector(Selector):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
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


class ArraySelector(Selector):
    def __init__(self, solid_color: str, **kwargs):
        super().__init__(**kwargs)
        with (
            self,
            v3.Template(v_slot_item="{ props }"),
            v3.VListItem(v_bind="props"),
            v3.Template(v_slot_prepend=""),
        ):
            v3.VIcon(
                v_if=(f"props.number_of_components == {MeshColoringMode.SOLID.value}",),
                icon="mdi-circle",
                color=(solid_color,),
            )
            v3.VIcon(
                v_if=(f"props.number_of_components >= {MeshColoringMode.ARRAY.value}",),
                icon=("props.number_of_components == 1 ? 'mdi-circle-medium' : 'mdi-arrow-top-right'",),
            )


class MeshDisplayColorUI(html.Div):
    def __init__(self, obj_display: str, color_presets: str, **kwargs):
        super().__init__(
            classes="display-property",
            **kwargs,
        )
        self.display = obj_display
        self.color_presets = color_presets
        self._build_ui()

    def _build_ui(self) -> None:
        with self:
            Text("Color", classes="text-header")
            ArraySelector(
                solid_color=f"{self.display}.solid_color",
                v_model=(f"{self.display}.active_array_id",),
                items=(f"{self.display}.data_arrays",),
                item_value="_id",
            )
            with Provider(name="active_array", instance=(f"{self.display}.active_array_id",)):
                with html.Div(
                    v_if=(f"active_array.coloring_mode == {MeshColoringMode.SOLID.value}",),
                ):
                    ColorPicker(v_model=(f"{self.display}.solid_color",))

                with Provider(
                    v_if=(f"active_array.coloring_mode == {MeshColoringMode.ARRAY.value}",),
                    name="array_color",
                    instance=(f"{self.display}.array_color._id",),
                ):
                    with html.Div(classes="display-property-setting"):
                        Text("Preset", classes="text-subtitle")
                        with (
                            PresetSelector(
                                v_model=("array_color.name"),
                                items=(self.color_presets,),
                            ),
                            v3.Template(v_slot_append=True),
                        ):
                            v3.VCheckbox(
                                v_model=("array_color.is_inverted",),
                                label="Invert",
                                hide_details=True,
                            )
                    with html.Div(classes="display-property-setting"):
                        Text("Range", classes="text-subtitle")
                        RangeSlider(
                            min=("active_array.array_min_max[0]",),
                            max=("active_array.array_min_max[1]",),
                            v_model="array_color.array_range",
                        )


class VolumeDisplayThreeDColorUI(html.Div):
    def __init__(self, obj_display: str, threed_presets: str, **kwargs):
        super().__init__(
            classes="display-property",
            **kwargs,
        )
        self.display = obj_display
        self.threed_presets = threed_presets
        self._build_ui()

    def _build_ui(self) -> None:
        with self:
            Text("Preset 3D", classes="text-header")
            (
                PresetSelector(
                    items=(self.threed_presets,),
                    v_model=(f"{self.display}.threed_color.name"),
                ),
            )
            with html.Div(classes="display-property-setting"):
                Text("Volume Rendering Shift", classes="text-subtitle")
                RangeSlider(
                    v_model=(f"{self.display}.threed_color.vr_shift",),
                    min=(f"{self.display}.scalar_range[0]",),
                    max=(f"{self.display}.scalar_range[1]",),
                )


class VolumeWindowLevelUI(html.Div):
    def __init__(self, obj_display: str, **kwargs):
        super().__init__(
            classes="display-property-setting",
            **kwargs,
        )
        self.display = obj_display
        self._build_ui()

    def _build_ui(self) -> None:
        with self:
            Text("Window / level", classes="text-subtitle")
            with (
                RangeSlider(
                    v_model=f"{self.display}.window_level",
                    min=(f"{self.display}.scalar_range[0]",),
                    max=(f"{self.display}.scalar_range[1]",),
                    disabled=(f"{self.display}.normal_color.show_arrows",),
                ),
                v3.Template(v_slot_append=True),
            ):
                Button(
                    tooltip="Auto Window/Level",
                    icon="mdi-refresh-auto",
                    click=f"{self.display}.window_level = {self.display}.scalar_range",
                    disabled=(f"{self.display}.normal_color.show_arrows",),
                )


class VolumeDisplayTwoDColorUI(html.Div):
    def __init__(self, obj_display: str, twod_presets: str, **kwargs):
        super().__init__(
            classes="display-property",
            **kwargs,
        )
        self.display = obj_display
        self.twod_presets = twod_presets
        self._build_ui()

    def _build_ui(self) -> None:
        with self:
            Text("Preset 2D", classes="text-header")
            with (
                PresetSelector(
                    items=(self.twod_presets,),
                    v_model=(f"{self.display}.twod_color.name"),
                ),
                v3.Template(v_slot_append=True),
            ):
                v3.VCheckbox(
                    v_model=(f"{self.display}.twod_color.is_inverted",),
                    label="Invert",
                    hide_details=True,
                )

            VolumeWindowLevelUI(self.display)


class VolumeDisplayNormalColorUI(html.Div):
    def __init__(self, obj_display: str, **kwargs):
        super().__init__(
            classes="display-property",
            **kwargs,
        )
        self.display = obj_display
        self._build_ui()

    def _build_ui(self) -> None:
        with self:
            Text("Color", classes="text-header")
            with html.Div(classes="display-property-setting"):
                Text("Arrows", classes="text-subtitle")
                Button(
                    icon=(f"{self.display}.normal_color.show_arrows ? 'mdi-eye-outline' : 'mdi-eye-off-outline'",),
                    tooltip=(f"{self.display}.normal_color.show_arrows ? 'Hide arrows' : 'Show arrows'",),
                    click=f"{self.display}.normal_color.show_arrows = !{self.display}.normal_color.show_arrows",
                )
                NumberInput(
                    v_model=(f"{self.display}.normal_color.sampling",),
                    disabled=(f"!{self.display}.normal_color.show_arrows",),
                    label="Sampling",
                    min=1,
                    max=100,
                    step=(1.0,),
                    suffix="%",
                )
                NumberInput(
                    v_model=(f"{self.display}.normal_color.arrow_length",),
                    disabled=(f"!{self.display}.normal_color.show_arrows",),
                    label="Length",
                    min=0.01,
                    max=20.0,
                    step=(1.0,),
                    precision=2,
                )
                NumberInput(
                    v_model=(f"{self.display}.normal_color.arrow_width",),
                    disabled=(f"!{self.display}.normal_color.show_arrows",),
                    label="Width",
                    min=0.01,
                    max=1.0,
                    step=(0.01,),
                    precision=2,
                )

            VolumeWindowLevelUI(self.display)
