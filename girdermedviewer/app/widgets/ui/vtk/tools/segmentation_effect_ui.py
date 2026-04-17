from dataclasses import dataclass

from trame.widgets import html
from trame.widgets import vuetify3 as v3
from trame_dataclass.v2 import Provider
from trame_server.utils.typed_state import TypedState

from ....utils import Button, SegmentationEffectType, Slider, Text


@dataclass
class SegmentationEffectState:
    active_effect: SegmentationEffectType = SegmentationEffectType.UNDEFINED
    active_effect_prop_id: str | None = None


class PaintEraseEffectUI(html.Div):
    def __init__(self, paint_erase_prop: str, **kwargs):
        super().__init__(**kwargs)
        self._paint_erase_prop = paint_erase_prop

        with self:
            Text("Brush size", subtitle=True)
            with (
                Slider(v_model=(f"{self._paint_erase_prop}.brush_size",), min=1, max=50, step=(1,)),
                v3.Template(v_slot_append=True),
            ):
                Button(
                    icon="mdi-sphere",
                    tooltip="Sphere brush",
                    click=f"{self._paint_erase_prop}.use_sphere_brush = !{self._paint_erase_prop}.use_sphere_brush",
                    active=(f"{self._paint_erase_prop}.use_sphere_brush",),
                )


class SegmentationEffectUI(v3.VCard):
    def __init__(self, **kwargs):
        super().__init__(variant="flat", title="Segmentation effect", **kwargs)

        self._typed_state = TypedState(self.state, SegmentationEffectState)

        self._build_ui()

    @property
    def active_effect(self) -> str:
        return self._typed_state.name.active_effect

    @property
    def active_effect_prop_id(self) -> str:
        return self._typed_state.name.active_effect_prop_id

    def _build_ui(self):
        with self:
            with html.Div(classes="d-flex justify-space-between"):
                self._build_effect_button(
                    icon="mdi-cursor-default",
                    effect_type=SegmentationEffectType.UNDEFINED,
                )
                self._build_effect_button(
                    icon="mdi-brush",
                    effect_type=SegmentationEffectType.PAINT,
                )
                self._build_effect_button(
                    icon="mdi-eraser",
                    effect_type=SegmentationEffectType.ERASE,
                )
            v3.VDivider(v_if=(f"!{self._is_active_effect(SegmentationEffectType.UNDEFINED)}",), classes="my-2")
            with Provider(name="active_effect_prop", instance=(self.active_effect_prop_id,)):
                PaintEraseEffectUI(
                    v_if=(
                        f"{self._is_active_effect(SegmentationEffectType.PAINT)} || {self._is_active_effect(SegmentationEffectType.ERASE)}",
                    ),
                    paint_erase_prop="active_effect_prop",
                )

    def _build_effect_button(self, effect_type: SegmentationEffectType, **kwargs):
        Button(
            tooltip=effect_type.value,
            active=(self._is_active_effect(effect_type),),
            click=self._set_active_effect(effect_type),
            **kwargs,
        )

    def _is_active_effect(self, effect_type: SegmentationEffectType) -> str:
        return f"({self.active_effect} === '{effect_type.value}')"

    def _set_active_effect(self, effect_type: SegmentationEffectType) -> str:
        return f"{self.active_effect} = '{effect_type.value}'"
