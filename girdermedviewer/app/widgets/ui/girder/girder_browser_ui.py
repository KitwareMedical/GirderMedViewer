import logging
from typing import Any

from trame.widgets import gwc, html
from trame.widgets import vuetify3 as v3
from undo_stack import Signal

from ...utils import Button, Text
from ..vtk.scene_ui import ObjectPropertyUI

logger = logging.getLogger(__name__)


class GirderBrowserUI(html.Div):
    row_clicked = Signal(dict)
    download_canceled = Signal(Any)
    item_deleted = Signal(Any)
    setting_changed = Signal(str, str)

    def __init__(self):
        super().__init__(classes="girder-browser")

        self._build_ui()

        self.item_list.item_card.download_canceled.connect(self.download_canceled)
        self.item_list.item_card.setting_window.item_deleted.connect(self.item_deleted)
        self.item_list.item_card.setting_window.item_settings.setting_changed.connect(self.setting_changed)

    def _build_ui(self):
        with self:
            self.file_manager = gwc.GirderFileManager(
                v_if=("location",),
                v_model_selected=("selected_in_location",),
                v_model_location=("location",),
                __properties=[
                    ("v_model_selected", "v-model:selected"),
                    ("v_model_location", "v-model:location"),
                ],
                row_click=(self.row_clicked, "[$event]"),
            )
            self.item_list = GirderItemList()


class GirderItemList(v3.VCard):
    def __init__(self, **kwargs):
        super().__init__(classes="mt-2", style="width: 100%; overflow: auto;", **kwargs)
        self._build_ui()

    def _build_ui(self):
        with (
            self,
            v3.VExpansionPanels(variant="accordion", focusable=True, multiple=True, v_model=("expanded_panels", [])),
        ):
            self.item_card = GirderItemCard(
                v_for="(item, item_id) in selected",
                item="item",
                item_id="item_id",
                value=("item_id",),
            )


class GirderItemCard(v3.VExpansionPanel):
    download_canceled = Signal(Any)

    def __init__(self, item, item_id, **kwargs):
        super().__init__(classes="item-card", **kwargs)
        self.item = item
        self.item_id = item_id
        self._build_ui()

    def _build_ui(self):
        with self:
            with v3.VExpansionPanelTitle():
                Text("{{ " + self.item + ".name }}")
                with v3.Template(v_slot_actions="{ expanded }"):
                    with (
                        v3.VTooltip(
                            v_if=(f"{self.item}.loading",),
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
                            click_native_stop=(self.download_canceled, f"[{self.item}]"),
                            __events=[("click_native_stop", "click.native.stop")],
                        )

                    v3.VIcon(
                        v_else=True,
                        icon=("expanded ? 'mdi-menu-up' : 'mdi-menu-down'",),
                    )

            with v3.VExpansionPanelText(v_if=(f"!{self.item}.loading",)):
                with (
                    v3.VRow(justify="center", classes="ma-1"),
                    v3.VItemGroup(
                        v_model=(f"{self.item}.window",),
                        mandatory=True,
                    ),
                    v3.VItem(
                        v_for="(card, n) in ['settings', 'info', 'metadata']",
                        v_slot="{ isSelected }",
                    ),
                ):
                    Button(
                        text="{{ card }}",
                        variant="text",
                        color=("isSelected ? 'primary' : 'grey'",),
                        click=(self.toggle_window, f"[n, {self.item}._id]"),
                    )

                with v3.VWindow(
                    v_model=(f"{self.item}.window",),
                ):
                    with v3.VWindowItem():
                        self.setting_window = ItemSettings(item=self.item, item_id=self.item_id)
                    with v3.VWindowItem():
                        ItemInfo(item=self.item)
                    with v3.VWindowItem():
                        ItemMetadata(item=self.item)

    def toggle_window(self, window_id, item_id):
        if item_id in self.state.selected:
            self.state.selected[item_id]["window"] = window_id
            self.state.dirty("selected")


class ItemSettings(v3.VCard):
    item_deleted = Signal(Any)

    def __init__(self, item, item_id, **kwargs):
        super().__init__(**kwargs)
        self.item = item
        self.item_id = item_id
        self._build_ui()

    def _build_ui(self):
        with self:
            with v3.VCardText():
                self.item_settings = ObjectPropertyUI(self.item_id)

            with v3.VCardActions(classes="justify-end"):
                Button(
                    text="Delete",
                    color="error",
                    click=(self.item_deleted, f"[{self.item}]"),
                )


class ItemInfo(v3.VCard):
    def __init__(self, item, **kwargs):
        super().__init__(**kwargs)
        self.item = item
        self._build_ui()

    def _build_ui(self):
        with self, v3.VCardText(), v3.VList(dense=True, classes="pa-0", subheader=True):
            v3.VListItem(
                "Size: {{ " + self.item + ".humanSize}}",
                classes="py-1 body-2",
            )
            v3.VListItem(
                "Created on {{ " + self.item + ".humanCreated}}",
                classes="py-1 body-2",
            )
            v3.VListItem(
                "Updated on {{ " + self.item + ".humanUpdated}}",
                classes="py-1 body-2",
            )


class ItemMetadata(v3.VList):
    def __init__(self, item, **kwargs):
        super().__init__(classes="metadata-list", **kwargs)
        self.item = item
        self._build_ui()

    def _build_ui(self):
        with self:
            with (
                v3.VListItem(v_for=f"(value, key) in {self.item}.meta", classes="metadata-item"),
                html.Div(classes="metadata-content"),
            ):
                Text("{{ key }}", classes="text-subtitle-2")
                Text("{{ value }}", classes="text-right text-body-2 metadata-ellipsis")

            v3.VDivider(
                v_if=(
                    f"Object.keys({self.item}.parentMeta).length > 0 && \
                        Object.keys({self.item}.meta).length > 0"
                )
            )

            with (
                v3.VListItem(v_for=f"(value, key) in {self.item}.meta", classes="metadata-item"),
                html.Div(classes="metadata-content"),
            ):
                Text("{{ key }}", classes="text-subtitle-2")
                Text("{{ value }}", classes="text-right text-body-2 metadata-ellipsis")
