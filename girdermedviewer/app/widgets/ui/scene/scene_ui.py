from typing import Any

from trame.widgets import html
from trame.widgets import vuetify3 as v3
from trame_dataclass.v2 import Provider, get_instance
from undo_stack import Signal

from ...utils import Button, Text
from .objects.object_display_ui import SceneObjectDisplayUI
from .objects.object_info_ui import SceneObjectInfoUI
from .objects.object_metadata_ui import SceneObjectMetadataUI


class SceneObjectUI(v3.VExpansionPanel):
    load_canceled = Signal(Any)
    delete_clicked = Signal(Any)

    def __init__(self, obj: str, scene: str, **kwargs) -> None:
        super().__init__(classes="item-card", **kwargs)
        self.obj = obj
        self.scene = scene
        self._build_ui()

    def _build_ui(self):
        with self:
            with v3.VExpansionPanelTitle():
                Text("{{ " + self.obj + ".name }}")
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

            with v3.VExpansionPanelText(v_if=(f"!{self.obj}.gui.loading",)):
                with (
                    v3.VRow(justify="center", classes="ma-1"),
                    v3.VItemGroup(
                        v_model=(f"{self.obj}.gui.current_window",),
                        mandatory=True,
                    ),
                ):
                    for window in ["display", "info", "metadata"]:
                        with v3.VItem(
                            v_slot="{ isSelected }",
                            value=window,
                        ):
                            Button(
                                text=window,
                                variant="text",
                                color=("isSelected ? 'primary' : 'grey'",),
                                click=f"{self.obj}.gui.current_window = '{window}'",
                            )

                with v3.VWindow(
                    v_model=(f"{self.obj}.gui.current_window",),
                ):
                    with (
                        v3.VWindowItem(
                            value="display",
                            v_if=(f"{self.obj}.display",),
                        ),
                        v3.VCard(),
                    ):
                        with v3.VCardText(classes="pt-0"), Provider(name="display", instance=(f"{self.obj}.display",)):
                            SceneObjectDisplayUI(
                                obj_display="display",
                                obj_type=f"{self.obj}.object_type",
                                threed_presets=f"{self.scene}.volume_presets",
                            )
                        with v3.VCardActions(classes="justify-end"):
                            Button(
                                text="Delete",
                                color="error",
                                click=(self.delete_clicked, f"[{self.obj}._id]"),
                            )
                    with v3.VWindowItem(value="info", v_if=(f"{self.obj}.info",)):
                        SceneObjectInfoUI(obj_info=f"{self.obj}.info")
                    with v3.VWindowItem(value="metadata", v_if=(f"{self.obj}.metadata",)):
                        SceneObjectMetadataUI(obj_metadata=f"{self.obj}.metadata")


class SceneUI(html.Div):
    load_canceled = Signal(str)
    delete_clicked = Signal(str)

    def __init__(self, **kwargs):
        super().__init__(classes="pa-2 fill-height", style="overflow: auto;", **kwargs)
        self.scene = get_instance(self.state.scene_id)
        self._build_ui()

        self.object_ui.load_canceled.connect(self.load_canceled)
        self.object_ui.delete_clicked.connect(self.delete_clicked)

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
