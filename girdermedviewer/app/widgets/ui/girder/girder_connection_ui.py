from dataclasses import dataclass

from trame.widgets import gwc
from trame.widgets import vuetify3 as v3
from trame_client.widgets.core import AbstractElement
from trame_server.utils.typed_state import TypedState
from undo_stack import Signal

from ...utils import Button


@dataclass
class GirderConnectionState:
    is_login_dialog_visible: bool = False
    girder_url: str | None = None
    girder_api_root: str | None = None
    girder_url_error: str | None = None
    girder_location: str | None = None
    girder_user_name: str | None = None


class GirderConnectionUI(AbstractElement):
    log_out_clicked = Signal()

    def __init__(self):
        super().__init__("girder-connection")
        self._typed_state = TypedState(self.state, GirderConnectionState)

        self._build_ui()

    def _build_ui(self):
        v3.VTextField(
            v_model=(self._typed_state.name.girder_url,),
            clearable=True,
            click_clear=f"{self._typed_state.name.girder_url} = null;",
            density="compact",
            disabled=(self._typed_state.name.girder_user_name,),
            error_messages=(self._typed_state.name.girder_url_error,),
            placeholder="Enter a Girder URL",
            style="width: 300px;",
        )
        v3.VSpacer()
        Button(
            v_if=(self._typed_state.name.girder_user_name,),
            click=self.log_out_clicked,
            size="large",
            text="{{ " + self._typed_state.name.girder_user_name + " }}",
            tooltip="Log out",
            variant="tonal",
        )
        with (
            Button(
                v_if=(f"!{self._typed_state.name.girder_user_name} && {self._typed_state.name.girder_api_root}",),
                text="Log In",
                size="large",
                variant="tonal",
            ),
            v3.VDialog(
                v_model=(f"{self._typed_state.name.is_login_dialog_visible}",),
                activator="parent",
                max_width=500,
            ),
            v3.VCard(),
            v3.VCardText(classes="pa-0"),
        ):
            gwc.GirderLogin(hide_forgot_password=True)
