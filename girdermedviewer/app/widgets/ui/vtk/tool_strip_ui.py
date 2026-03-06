import logging

from trame.widgets import html
from trame_server.utils.typed_state import TypedState

from ...utils import Button
from .base_view import ViewState
from .position_menu import PositionMenu

logger = logging.getLogger(__name__)


class ToolStripUI(html.Div):
    def __init__(self, disabled: str, **kwargs):
        super().__init__(
            classes="tools-strip",
            **kwargs,
        )
        self._typed_state = TypedState(self.state, ViewState)

        with self:
            Button(
                click=self._toggle_obliques_visibility,
                disabled=(disabled,),
                color=(f"{self._typed_state.name.are_obliques_visible} && !{disabled} ? 'primary' : 'undefined'",),
                icon="mdi-cube-scan",
                tooltip=(f"{self._typed_state.name.are_obliques_visible} ? 'Hide obliques' : 'Show obliques'",),
                variant="text",
                size="default",
            )

            Button(
                click=self.ctrl.reset,
                disabled=(disabled,),
                icon="mdi-camera-flip-outline",
                tooltip="Reset views",
                variant="text",
                size="default",
            )

            PositionMenu(
                disabled=(disabled,),
                color=(f"{self._typed_state.name.is_position_menu_visible} && !{disabled} ? 'primary' : 'undefined'",),
                icon="mdi-target",
                tooltip=(
                    f"{self._typed_state.name.is_position_menu_visible} ? 'Hide position dialog' : 'Show position dialog'",
                ),
                variant="text",
                size="default",
            )

    def _toggle_obliques_visibility(self):
        self._typed_state.data.are_obliques_visible = not self._typed_state.data.are_obliques_visible
