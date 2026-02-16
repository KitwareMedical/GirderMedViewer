import logging
from dataclasses import dataclass, field
from typing import Any

from trame.widgets import gwc
from trame.widgets import vuetify3 as v3
from trame_server.utils.typed_state import TypedState
from undo_stack import Signal

from ...utils import Button, Text

logger = logging.getLogger(__name__)


@dataclass
class GirderBrowserState:
    selected_in_location: list[dict[str, str]] = field(default_factory=list)
    location: dict[str, str] | None = None
    is_browser_dialog_visible: bool = False


class GirderBrowserUI(Button):
    row_clicked = Signal(dict[str, Any])
    location_updated = Signal(dict[str, Any])

    def __init__(self, **kwargs):
        super().__init__(icon="mdi-file-plus-outline", tooltip="Browse data", size="default", **kwargs)
        self._typed_state = TypedState(self.state, GirderBrowserState)
        self._build_ui()

    def _close(self):
        self._typed_state.data.is_browser_dialog_visible = False

    def _build_ui(self):
        with (
            self,
            v3.VDialog(v_model=(self._typed_state.name.is_browser_dialog_visible,), activator="parent", width=800),
            v3.VCard(title="Select data"),
        ):
            with v3.VCardText(classes="pa-0 d-flex justify-center"):
                gwc.GirderFileManager(
                    classes="girder-browser",
                    v_if=(self._typed_state.name.location,),
                    selected=(self._typed_state.name.selected_in_location,),
                    location=(self._typed_state.name.location,),
                    update_location=(self.location_updated, "[$event]"),
                    row_click=(self.row_clicked, "[$event]"),
                )
                Text(
                    "No data to show. You must log in.",
                    v_else=True,
                    classes="mb-4 font-italic",
                )
            with v3.VCardActions(classes="justify-end"):
                Button(text="Done", variant="tonal", click=self._close)
