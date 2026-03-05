from trame.widgets import html
from trame.widgets import vuetify3 as v3
from trame_dataclass.v2 import Provider
from undo_stack import Signal

from ....utils import Button, ColorPicker, SegmentationEffectType, Text, TextField
from ..objects.object_components import PropertySlider


class PaintEraseEffectUI(html.Div):
    def __init__(self, paint_erase_prop: str, **kwargs):
        super().__init__(**kwargs)
        self._paint_erase_prop = paint_erase_prop

        with self:
            Text("Brush size", subtitle=True)
            with (
                PropertySlider(v_model=(f"{self._paint_erase_prop}.brush_size",)),
                v3.Template(v_slot_append=True),
            ):
                Button(
                    icon="mdi-sphere",
                    tooltip="Sphere brush",
                    click=f"{self._paint_erase_prop}.use_sphere_brush = !{self._paint_erase_prop}.use_sphere_brush",
                    active=(f"{self._paint_erase_prop}.use_sphere_brush",),
                )


class SegmentColorDialog(v3.VDialog):
    def __init__(self, segment: str, **kwargs):
        super().__init__(v_model=(f"{segment}.is_color_dialog_visible",), width=500, **kwargs)
        self._segment = segment
        self._build_ui()

    def _build_ui(self):
        with self, v3.VCard():
            with v3.VCardTitle(classes="d-flex justify-space-between align-center"):
                Text("Edit segment color")
                Button(icon="mdi-close", size="small", click=f"{self._segment}.is_color_dialog_visible = false;")
            with v3.VCardText():
                ColorPicker(v_model=(f"{self._segment}.color",))


class SegmentList(v3.VList):
    """
    List view for the current active segments.
    """

    delete_segment_clicked = Signal(str, str)

    def __init__(self, obj_id: str, active_segment_id: str, segments: str, **kwargs) -> None:
        super().__init__(classes="segment-list", **kwargs)
        self._obj_id = obj_id
        self._segment_list = segments
        self._active_segment_id = active_segment_id

        self._build_ui()

    def _build_ui(self):
        with (
            self,
            v3.VListItem(
                classes="segment-list-item",
                v_for=f"(segment, i) in {self._segment_list}",
                key="i",
                value="segment",
                active=(f"segment._id === {self._active_segment_id}",),
                click=f"{self._active_segment_id} = segment._id;",
            ),
        ):
            with (
                v3.Template(v_slot_prepend=True),
                Button(
                    icon="mdi-circle",
                    color=("segment.color",),
                ),
            ):
                SegmentColorDialog(segment="segment", activator="parent")

            with v3.Template(v_slot_default=True):
                TextField(
                    v_model=("segment.name",),
                    disabled=(f"segment._id !== {self._active_segment_id}",),
                )

            with v3.Template(v_slot_append=True):
                v3.VIcon(
                    classes="mr-2",
                    icon=("segment.is_visible ? 'mdi-eye-outline' : 'mdi-eye-off-outline'",),
                    click_native_stop="segment.is_visible = !segment.is_visible;",
                    __events=[("click_native_stop", "click.native.stop")],
                )
                v3.VIcon(
                    icon="mdi-delete-outline",
                    click_native_stop=(self.delete_segment_clicked, f"[{self._obj_id}, segment._id]"),
                    __events=[("click_native_stop", "click.native.stop")],
                )


class SegmentationFilterUI(html.Div):
    add_segment_clicked = Signal(str)
    delete_segment_clicked = Signal(str, str)

    def __init__(self, obj_id: str, obj_filter_prop: str, **kwargs):
        super().__init__(**kwargs)
        self._obj_id = obj_id
        self._filter_prop = obj_filter_prop

        self._build_ui()

    @property
    def segments(self) -> str:
        return f"{self._filter_prop}.segments"

    @property
    def active_segment_id(self) -> str:
        return f"{self._filter_prop}.active_segment_id"

    @property
    def active_effect(self) -> str:
        return f"{self._filter_prop}.active_effect"

    @property
    def active_effect_prop_id(self) -> str:
        return f"{self._filter_prop}.active_effect_prop_id"

    def _build_ui(self):
        with self:
            with html.Div(v_if=(self.active_segment_id,)):
                with v3.VCard(variant="flat"):
                    with v3.VCardText(style="height: calc(100% - 64px); overflow-y: auto;"):
                        self._build_segment_list()

                    with v3.VCardActions(classes="justify-center", style="height: 64px;"):
                        Button(
                            variant="tonal",
                            tooltip="Add Segment",
                            icon="mdi-plus",
                            click=(self.add_segment_clicked, f"[{self._obj_id}]"),
                        )
                v3.VDivider()
                with v3.VCard(variant="flat"):
                    with v3.VCardItem(), html.Div(classes="d-flex justify-space-between"):
                        self._build_effect_buttons()
                    v3.VDivider(classes="mx-3")
                    with (
                        v3.VCardText(v_if=(self.active_effect_prop_id,), classes="align-center"),
                    ):
                        self._build_effect_uis()

            with html.Div(v_else=True, classes="d-flex justify-center"):
                Button(
                    classes="ma-4",
                    click=(self.add_segment_clicked, f"[{self._obj_id}]"),
                    prepend_icon="mdi-plus",
                    text="Add segment",
                    variant="tonal",
                )

    def _build_effect_button(self, effect_type: SegmentationEffectType, **kwargs):
        Button(
            tooltip=effect_type.value,
            active=(self._is_active_effect(effect_type),),
            click=self._set_active_effect(effect_type),
            **kwargs,
        )

    def _build_effect_buttons(self):
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

    def _build_effect_uis(self):
        with Provider(name="active_effect_prop", instance=(self.active_effect_prop_id,)):
            PaintEraseEffectUI(
                v_if=(self._is_active_effect(SegmentationEffectType.PAINT),),
                paint_erase_prop="active_effect_prop",
            )
            PaintEraseEffectUI(
                v_if=(self._is_active_effect(SegmentationEffectType.ERASE),),
                paint_erase_prop="active_effect_prop",
            )

    def _build_segment_list(self):
        self.segment_list = SegmentList(
            obj_id=self._obj_id,
            active_segment_id=self.active_segment_id,
            segments=self.segments,
        )
        self.segment_list.delete_segment_clicked.connect(self.delete_segment_clicked)

    def _is_active_effect(self, effect_type: SegmentationEffectType) -> str:
        return f"{self.active_effect} === '{effect_type.value}'"

    def _set_active_effect(self, effect_type: SegmentationEffectType) -> str:
        return f"{self.active_effect} = '{effect_type.value}'"
