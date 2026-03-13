from dataclasses import dataclass, field
from typing import Any

from trame.widgets import html
from trame.widgets import vuetify3 as v3
from trame_dataclass.v2 import Provider, get_instance
from trame_server.utils.typed_state import TypedState
from undo_stack import Signal

from ...utils import Button, FilterType, Text
from .filters.filter_ui import FilterToolbarUI, FilterUI
from .objects.object_display_ui import SceneObjectDisplayUI
from .objects.object_info_ui import SceneObjectInfoUI
from .objects.object_metadata_ui import SceneObjectMetadataUI


@dataclass
class SceneState:
    scene_id: str | None = None
    active_primary_volume_id: str | None = None
    primary_volume_ids: list[str] = field(default_factory=list)


class SceneObjectUI(v3.VExpansionPanel):
    load_canceled = Signal(Any)
    filter_clicked = Signal(str, FilterType)
    delete_clicked = Signal(str)

    def __init__(self, obj: str, scene: str, **kwargs) -> None:
        super().__init__(classes="item-card", **kwargs)
        self.obj = obj
        self.scene = scene
        self._build_ui()

        self.filter_toolbar.filter_clicked.connect(self.filter_clicked)

    def _build_ui(self):
        with self:
            with v3.VExpansionPanelTitle():
                Text("{{ " + self.obj + ".name }}", classes="text-header")
                with v3.Template(v_slot_actions="{ expanded }"):
                    with (
                        v3.VTooltip(
                            v_if=(f"{self.obj}.gui.loading",),
                            close_delay=100,
                            text="Cancel download",
                        ),
                        v3.Template(v_slot_activator="{ props }"),
                    ):
                        v3.VProgressCircular(
                            v_bind="props",
                            size=20,
                            indeterminate=True,
                            width=3,
                            click_native_stop=(self.load_canceled, f"[{self.obj}._id]"),
                            __events=[("click_native_stop", "click.native.stop")],
                        )

                    v3.VIcon(
                        v_else=True,
                        icon=("expanded ? 'mdi-menu-up' : 'mdi-menu-down'",),
                    )

            with v3.VExpansionPanelText(v_if=(f"!{self.obj}.gui.loading",)), v3.VCard():
                with (
                    v3.VCardTitle(classes="d-flex justify-center"),
                    v3.VItemGroup(
                        v_model=(f"{self.obj}.gui.current_window",),
                        mandatory=True,
                    ),
                ):
                    with v3.VItem(
                        v_if=(f"{self.obj}.filter_type",),
                        v_slot="{ isSelected }",
                        value="filter",
                    ):
                        Button(
                            text="{{ " + f"{self.obj}.filter_type" + " }}",
                            variant="text",
                            color=("isSelected ? 'primary' : 'grey'",),
                            click=f"{self.obj}.gui.current_window = 'filter'",
                        )
                    with v3.VItem(
                        v_if=(f"{self.obj}.display",),
                        v_slot="{ isSelected }",
                        value="display",
                    ):
                        Button(
                            text="display",
                            variant="text",
                            color=("isSelected ? 'primary' : 'grey'",),
                            click=f"{self.obj}.gui.current_window = 'display'",
                        )

                    with v3.VItem(
                        v_if=(f"{self.obj}.info",),
                        v_slot="{ isSelected }",
                        value="info",
                    ):
                        Button(
                            text="info",
                            variant="text",
                            color=("isSelected ? 'primary' : 'grey'",),
                            click=f"{self.obj}.gui.current_window = 'info'",
                        )

                    with v3.VItem(
                        v_if=(f"{self.obj}.metadata",),
                        v_slot="{ isSelected }",
                        value="metadata",
                    ):
                        Button(
                            text="metadata",
                            variant="text",
                            color=("isSelected ? 'primary' : 'grey'",),
                            click=f"{self.obj}.gui.current_window = 'metadata'",
                        )

                with (
                    v3.VCardText(),
                    v3.VWindow(v_model=(f"{self.obj}.gui.current_window",), style="overflow: unset;"),
                ):
                    with (
                        v3.VWindowItem(value="filter", v_if=(f"{self.obj}.filter_type",)),
                        Provider(name="filter_prop", instance=(f"{self.obj}.filter_prop_id",)),
                    ):
                        FilterUI(
                            obj_id=f"{self.obj}._id",
                            obj_filter_type=f"{self.obj}.filter_type",
                            obj_filter_prop="filter_prop",
                        )

                    with (
                        v3.VWindowItem(value="display", v_if=(f"{self.obj}.display",)),
                        Provider(name="display", instance=(f"{self.obj}.display",)),
                    ):
                        SceneObjectDisplayUI(
                            obj_display="display",
                            obj_type=f"{self.obj}.object_type",
                            threed_presets=f"{self.scene}.volume_presets",
                        )

                    with v3.VWindowItem(value="info", v_if=(f"{self.obj}.info",)):
                        SceneObjectInfoUI(obj_info=f"{self.obj}.info")

                    with v3.VWindowItem(value="metadata", v_if=(f"{self.obj}.metadata",)):
                        SceneObjectMetadataUI(obj_metadata=f"{self.obj}.metadata")

                with v3.VCardActions(classes="justify-space-between"):
                    self.filter_toolbar = FilterToolbarUI(obj_id=f"{self.obj}._id", obj_type=f"{self.obj}.object_type")

                    Button(
                        icon="mdi-delete",
                        tooltip="Delete",
                        color="error",
                        click=(self.delete_clicked, f"[{self.obj}._id]"),
                    )


class SceneUI(html.Div):
    load_canceled = Signal(str)
    filter_clicked = Signal(str, FilterType)
    delete_clicked = Signal(str)

    def __init__(self, **kwargs):
        super().__init__(classes="pa-2 fill-height", style="overflow: auto;", **kwargs)
        self._typed_state = TypedState(self.state, SceneState)
        self.scene = get_instance(self._typed_state.data.scene_id)
        self._build_ui()

        self.object_ui.load_canceled.connect(self.load_canceled)
        self.object_ui.delete_clicked.connect(self.delete_clicked)
        self.object_ui.filter_clicked.connect(self.filter_clicked)

    def _build_ui(self):
        with self, self.scene.provide_as("scene"):
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
                classes="d-flex justify-center font-italic fill-height align-center",
                text="Select data to get started",
            )
