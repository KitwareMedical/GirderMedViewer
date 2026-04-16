from typing import Any

from trame.widgets import html
from trame.widgets import vuetify3 as v3
from trame_dataclass.v2 import get_instance
from trame_server.utils.typed_state import TypedState
from undo_stack import Signal

from ...utils import (
    Button,
    FilterType,
    LayerButton,
    LoadingButton,
    SceneObjectSubtype,
    SceneObjectType,
    Text,
)
from .filters.filter_ui import FilterToolbarUI, FilterUI
from .objects.object_display_ui import SceneObjectDisplayUI
from .objects.object_info_ui import SceneObjectInfoUI
from .objects.object_metadata_ui import SceneObjectMetadataUI
from .scene_state import SceneState


class SceneObjectUI(v3.VExpansionPanel):
    load_canceled = Signal(Any)
    delete_clicked = Signal(str)
    visibility_clicked = Signal(str)
    overlay_clicked = Signal(str)

    def __init__(self, obj: str, scene: str, **kwargs) -> None:
        super().__init__(classes="item-card", **kwargs)

        self._typed_state = TypedState(self.state, SceneState)
        self._obj = obj
        self._scene = scene
        self._build_ui()

    def _is_labelmap(self) -> str:
        return f"({self._obj}.object_subtype === '{SceneObjectSubtype.LABELMAP.value}')"

    def _is_active_labelmap(self) -> str:
        return f"({self._typed_state.name.active_labelmap_id} === {self._obj}._id)"

    def _is_volume(self, include_labelmap: bool = False) -> str:
        is_volume = f"({self._obj}.object_type === '{SceneObjectType.VOLUME.value}')"
        if include_labelmap:
            return f"({is_volume})"
        return f"({is_volume} && !{self._is_labelmap()})"

    def _is_primary_volume(self) -> str:
        return f"{self._typed_state.name.primary_volume_ids}.includes({self._obj}._id)"

    def _is_active_primary_volume(self) -> str:
        return f"({self._typed_state.name.active_primary_volume_id} === {self._obj}._id)"

    def _is_disabled(self) -> str:
        return f"!{self._obj}.is_visible"

    def _build_ui(self):
        with self:
            with v3.VExpansionPanelTitle(classes="item-card-title", v_if=(f"{self._obj}.gui.loading",)):
                Text("{{ " + self._obj + ".name }}", classes="text-header font-weight-medium")
                with v3.Template(v_slot_actions="{ expanded }"):
                    LoadingButton(
                        tooltip="Cancel",
                        click_stop=(self.load_canceled, f"[{self._obj}._id]"),
                    )

            with v3.VExpansionPanelTitle(classes="item-card-title", v_else=True):
                v3.VIcon(
                    icon=(f"{self._obj}.gui.icon",),
                    color=(f"{self._is_active_labelmap()} ? 'primary' : 'undefined'",),
                )
                Text("{{ " + self._obj + ".name }}", classes="text-header font-weight-medium")
                v3.VChip(
                    v_if=(self._is_active_primary_volume(),),
                    color="primary",
                    text="main",
                )
                with v3.Template(v_slot_actions="{ expanded }"):
                    Button(
                        click_stop=(self.visibility_clicked, f"[{self._obj}._id]"),
                        icon=(f"{self._obj}.is_visible ? 'mdi-eye-outline' : 'mdi-eye-off-outline'",),
                        tooltip=(f"{self._obj}.is_visible ? 'Hide' : 'Show'",),
                    )

            with v3.VExpansionPanelText(v_if=(f"!{self._obj}.gui.loading",)), v3.VCard():
                with (
                    v3.VCardTitle(classes="d-flex justify-center"),
                    v3.VItemGroup(
                        v_model=(f"{self._obj}.gui.current_window",),
                        mandatory=True,
                    ),
                ):
                    with v3.VItem(
                        v_if=(f"{self._obj}.filter_type",),
                        v_slot="{ isSelected }",
                        value="filter",
                    ):
                        Button(
                            text="{{ " + f"{self._obj}.filter_type" + " }}",
                            variant="text",
                            color=("isSelected ? 'primary' : 'grey'",),
                            click=f"{self._obj}.gui.current_window = 'filter'",
                        )
                    with v3.VItem(
                        v_if=(f"{self._obj}.display",),
                        v_slot="{ isSelected }",
                        value="display",
                    ):
                        Button(
                            text="display",
                            variant="text",
                            color=("isSelected ? 'primary' : 'grey'",),
                            click=f"{self._obj}.gui.current_window = 'display'",
                        )

                    with v3.VItem(
                        v_if=(f"{self._obj}.info",),
                        v_slot="{ isSelected }",
                        value="info",
                    ):
                        Button(
                            text="info",
                            variant="text",
                            color=("isSelected ? 'primary' : 'grey'",),
                            click=f"{self._obj}.gui.current_window = 'info'",
                        )

                    with v3.VItem(
                        v_if=(f"{self._obj}.metadata",),
                        v_slot="{ isSelected }",
                        value="metadata",
                    ):
                        Button(
                            text="metadata",
                            variant="text",
                            color=("isSelected ? 'primary' : 'grey'",),
                            click=f"{self._obj}.gui.current_window = 'metadata'",
                        )

                with (
                    v3.VCardText(),
                    v3.VWindow(v_model=(f"{self._obj}.gui.current_window",), style="overflow: unset;"),
                ):
                    with (
                        v3.VWindowItem(value="filter", v_if=(f"{self._obj}.filter_type",)),
                    ):
                        self.filter_ui = FilterUI(
                            obj=self._obj,
                            disabled=self._is_disabled(),
                        )

                    with (
                        v3.VWindowItem(value="display", v_if=(f"{self._obj}.display",)),
                    ):
                        SceneObjectDisplayUI(
                            obj=self._obj,
                            disabled=self._is_disabled(),
                            has_opacity=f"!{self._is_primary_volume()}",
                            color_presets=f"{self._scene}.color_presets",
                            volume_presets=f"{self._scene}.volume_presets",
                        )

                    with v3.VWindowItem(value="info", v_if=(f"{self._obj}.info",)):
                        SceneObjectInfoUI(obj_info=f"{self._obj}.info")

                    with v3.VWindowItem(value="metadata", v_if=(f"{self._obj}.metadata",)):
                        SceneObjectMetadataUI(obj_metadata=f"{self._obj}.metadata")

                with v3.VCardActions():
                    self.filter_toolbar = FilterToolbarUI(
                        v_if=(f"!{self._is_labelmap()}",),
                        obj_id=f"{self._obj}._id",
                        obj_type=f"{self._obj}.object_type",
                    )
                    v3.VSpacer()
                    with html.Div(classes="d-flex"):
                        LayerButton(
                            v_if=(f"{self._is_volume()} && !{self._is_active_primary_volume()}",),
                            main_layer=(self._is_primary_volume(),),
                            tooltip=(f"{self._is_primary_volume()} ? 'Set as overlay' : 'Set as main'",),
                            click=(self.overlay_clicked, f"[{self._obj}._id]"),
                        )
                        Button(
                            icon="mdi-delete",
                            tooltip="Delete",
                            color="error",
                            click=(self.delete_clicked, f"[{self._obj}._id]"),
                        )


class SceneUI(html.Div):
    load_canceled = Signal(str)
    filter_clicked = Signal(str, FilterType)
    delete_clicked = Signal(str)
    add_segment_clicked = Signal(str)
    delete_segment_clicked = Signal(str, str)
    segment_clicked = Signal(str, str)
    visibility_clicked = Signal(str)
    overlay_clicked = Signal(str)

    def __init__(self, **kwargs):
        super().__init__(classes="scene-drawer", **kwargs)
        self._typed_state = TypedState(self.state, SceneState)
        self._scene = get_instance(self._typed_state.data.scene_id)
        self._build_ui()

        self.object_ui.load_canceled.connect(self.load_canceled)
        self.object_ui.delete_clicked.connect(self.delete_clicked)
        self.object_ui.visibility_clicked.connect(self.visibility_clicked)
        self.object_ui.overlay_clicked.connect(self.overlay_clicked)
        self.object_ui.filter_toolbar.filter_clicked.connect(self.filter_clicked)
        self.object_ui.filter_ui.segmentation_filter.add_segment_clicked.connect(self.add_segment_clicked)
        self.object_ui.filter_ui.segmentation_filter.delete_segment_clicked.connect(self.delete_segment_clicked)
        self.object_ui.filter_ui.segmentation_filter.segment_clicked.connect(self.segment_clicked)

    def _build_ui(self):
        with self, self._scene.provide_as("scene"):
            with v3.VExpansionPanels(
                v_if=("scene.objects?.length > 0",),
                v_model=("scene.gui.expanded_objects",),
                variant="accordion",
                focusable=True,
                multiple=True,
            ):
                self.object_ui = SceneObjectUI(
                    obj="obj",
                    scene="scene",
                    v_for="obj in scene.objects",
                    readonly=("obj.gui.loading",),
                    value=("obj._id",),
                )
            Text(
                v_else=True,
                classes="d-flex justify-center font-italic",
                text="Select data to get started",
            )
