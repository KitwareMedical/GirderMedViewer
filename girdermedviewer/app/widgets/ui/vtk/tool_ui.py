import logging
from dataclasses import dataclass
from enum import Enum

from trame.widgets import html
from trame.widgets import vuetify3 as v3
from trame_server.utils.typed_state import TypedState

from ...utils import Button
from .base_view import ViewState
from .tools.place_point_ui import PlacePointUI

logger = logging.getLogger(__name__)


class ToolType(Enum):
    UNDEFINED = 0
    PLACE_POINT = 1


@dataclass
class ToolState:
    active_tool: ToolType = ToolType.UNDEFINED


class ToolUI(html.Div):
    def __init__(self, disabled: str, **kwargs):
        super().__init__(
            classes="tools-strip",
            **kwargs,
        )
        self._views_state = TypedState(self.state, ViewState)
        self._typed_state = TypedState(self.state, ToolState)

        with self:
            Button(
                click=self._toggle_obliques_visibility,
                disabled=(disabled,),
                color=(f"{self._views_state.name.are_obliques_visible} && !{disabled} ? 'primary' : 'undefined'",),
                icon="mdi-cube-scan",
                tooltip=(f"{self._views_state.name.are_obliques_visible} ? 'Hide obliques' : 'Show obliques'",),
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

            Button(
                click=lambda: self._activate_tool(ToolType.PLACE_POINT),
                disabled=(disabled,),
                color=(f"{self._is_tool_active(ToolType.PLACE_POINT)} && !{disabled} ? 'primary' : 'undefined'",),
                icon="mdi-target",
                tooltip="Place point",
                variant="text",
                size="default",
            )

    def _toggle_obliques_visibility(self):
        self._views_state.data.are_obliques_visible = not self._views_state.data.are_obliques_visible

    def _activate_tool(self, tool_type: ToolType) -> None:
        if self._typed_state.data.active_tool == tool_type:
            self._typed_state.data.active_tool = ToolType.UNDEFINED
        else:
            self._typed_state.data.active_tool = tool_type

    def _is_tool_active(self, tool_type: ToolType) -> str:
        return f"({self._typed_state.name.active_tool} === {tool_type.value})"

    def build_active_tool_ui(self):
        with html.Div():
            v3.VDivider(v_if=(f"!{self._is_tool_active(ToolType.UNDEFINED)}",))
            PlacePointUI(v_if=(self._is_tool_active(ToolType.PLACE_POINT),))
