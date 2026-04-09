from trame.widgets import html
from trame.widgets import vuetify3 as v3
from trame_server.utils.typed_state import TypedState
from undo_stack import Signal

from ....utils import Button, ColorPicker, Text, TextField
from ..scene_state import SceneState


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

        self._scene_state = TypedState(self.state, SceneState)

        self._build_ui()

    @property
    def segments(self) -> str:
        return f"{self._filter_prop}.segments"

    @property
    def active_segment_id(self) -> str:
        return self._scene_state.name.active_segment_id

    def _build_ui(self):
        with self:
            with html.Div(v_if=(f"{self.segments}?.length > 0",)):
                self._build_segment_list()
                with html.Div(classes="d-flex justify-center"):
                    Button(
                        variant="tonal",
                        tooltip="Add Segment",
                        icon="mdi-plus",
                        click=(self.add_segment_clicked, f"[{self._obj_id}]"),
                    )

            with html.Div(v_else=True, classes="d-flex justify-center"):
                Button(
                    click=(self.add_segment_clicked, f"[{self._obj_id}]"),
                    prepend_icon="mdi-plus",
                    text="Add segment",
                    variant="tonal",
                )

    def _build_segment_list(self):
        self.segment_list = SegmentList(
            obj_id=self._obj_id,
            active_segment_id=self.active_segment_id,
            segments=self.segments,
        )
        self.segment_list.delete_segment_clicked.connect(self.delete_segment_clicked)
