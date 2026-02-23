from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from trame.widgets import html
from trame.widgets import vuetify3 as v3
from trame_server.utils.typed_state import TypedState
from undo_stack import Signal

from ...utils import Button, Text


@dataclass
class Preset:
    title: str
    props: dict[str, str]


@dataclass
class RangeSliderState:
    min_value: float = 0
    max_value: float = 1
    value: list[float] = field(default_factory=lambda: [0.0, 0.5])
    step: float = 1e-6
    is_reversed: bool = False


@dataclass
class SceneObjectPropertyState:
    is_primary_volume: bool = True
    window_level: RangeSliderState = field(default_factory=RangeSliderState)
    preset_range: RangeSliderState = field(default_factory=RangeSliderState)
    preset_name: str = ""
    color: str = ""
    opacity: float = 1.0


class SceneObjectType(Enum):
    MESH = "mesh"
    VOLUME = "volume"


@dataclass
class SceneObjectState:
    object_type: SceneObjectType
    properties: SceneObjectPropertyState


@dataclass
class SceneState:
    presets: list[Preset]
    objects: dict[str, SceneObjectState] = field(default_factory=dict)


class ObjectPropertyUI(html.Div):
    setting_changed = Signal(str, Any, str)
    auto_window_level_clicked = Signal()

    def __init__(self, object_id: str, **kwargs):
        super().__init__(
            classes="d-flex flex-column",
            **kwargs,
        )
        self.object_id = object_id
        self._typed_state = TypedState(self.state, SceneState)

        self._build_ui()

    def _get_setting(self, setting: str) -> str:
        return f"{self._typed_state.name.objects}[{self.object_id}].properties.{setting}"

    def _is_volume(self) -> str:
        return f"{self._typed_state.name.objects}[{self.object_id}].object_type === '{SceneObjectType.VOLUME.value}'"

    def _is_mesh(self) -> str:
        return f"{self._typed_state.name.objects}[{self.object_id}].object_type === '{SceneObjectType.MESH.value}'"

    def _has_opacity(self) -> str:
        return f"{self._is_mesh()} || !{self._get_setting('is_primary_volume')}"

    def _send_property_changed_signal(self, prop: str):
        return (self.setting_changed, f"['{prop}', $event, {self.object_id}]")

    def _build_ui(self) -> None:
        with self:
            with html.Div(v_if=(self._is_volume(),)):
                Text("Preset", classes="text-subtitle-2 pt-2")
                with v3.VSelect(
                    items=(self._typed_state.name.presets,),
                    v_model=(self._get_setting("preset_name"),),
                    update_modelValue=self._send_property_changed_signal("preset_name"),
                    variant="solo-filled",
                    flat=True,
                ):
                    with (
                        v3.Template(v_slot_item="{ props }"),
                        v3.VListItem(v_bind="props"),
                        v3.Template(v_slot_prepend=""),
                    ):
                        v3.VImg(v_if=("props.data",), src=("props.data",), height=64, width=64, classes="mr-2")

                    with v3.Template(v_slot_selection="{item}"):
                        v3.VImg(
                            v_if=("item.props.data",), src=("item.props.data",), height=32, width=32, classes="mr-2"
                        )
                        html.Span("{{ item.title }}")

                Text("Volume Rendering Shift", classes="text-subtitle-2 pt-2")
                ObjectPropertyRangeSlider(
                    object_id=self.object_id,
                    property="preset_range",
                    typed_state=self._typed_state,
                    update_modelValue=self._send_property_changed_signal("preset_range"),
                )

                with html.Div(v_if=(self._get_setting("is_primary_volume"),)):
                    Text("Window / level", classes="text-subtitle-2 pt-2")
                    with (
                        ObjectPropertyRangeSlider(
                            object_id=self.object_id,
                            property="window_level",
                            typed_state=self._typed_state,
                            update_modelValue=self._send_property_changed_signal("window_level"),
                        ),
                        v3.Template(v_slot_append=True),
                    ):
                        Button(
                            tooltip="Auto Window/Level",
                            icon="mdi-refresh-auto",
                            click=self.auto_window_level_clicked,
                        )

            with html.Div(v_if=(self._has_opacity(),)):
                Text("Opacity", classes="text-subtitle-2 pt-2")
                v3.VSlider(
                    min=0,
                    max=1,
                    v_model=(self._get_setting("opacity"),),
                    update_modelValue=self._send_property_changed_signal("opacity"),
                    step=1e-6,
                    hide_details=True,
                )

            with html.Div(v_if=(self._is_mesh(),)):
                Text("Color", classes="text-subtitle-2 pt-2")
                v3.VColorPicker(
                    v_model=(self._get_setting("color"),),
                    update_modelValue=self._send_property_changed_signal("color"),
                    elevation=0,
                    modes=("['rgb']",),
                    style="width: 100%",
                )


class ObjectPropertyRangeSlider(v3.VRangeSlider):
    def __init__(self, object_id: str, property: str, typed_state: TypedState[SceneState], **kwargs):
        self._typed_state = typed_state
        self._object_id = object_id
        self._property = property

        super().__init__(
            min=(self._get_slider_setting("min_value"),),
            max=(self._get_slider_setting("max_value"),),
            v_model=(self._get_slider_setting("value"),),
            step=(self._get_slider_setting("step"),),
            is_reversed=(self._get_slider_setting("is_reversed"),),
            hide_details=True,
            **kwargs,
        )

    def _get_slider_setting(self, setting: str) -> str:
        return f"{self._typed_state.name.objects}[{self._object_id}].properties.{self._property}.{setting}"
