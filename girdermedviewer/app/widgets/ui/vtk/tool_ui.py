import logging
from dataclasses import dataclass
from enum import Enum

from trame.widgets import html
from trame.widgets import vuetify3 as v3
from trame_server.utils.typed_state import TypedState

from ...utils import Button
from .tools.place_point_ui import PlacePointUI
from .tools.place_roi_ui import PlaceROIUI
from .tools.segmentation_effect_ui import SegmentationEffectUI
from .views_ui import ViewsState

logger = logging.getLogger(__name__)


class ToolType(Enum):
    UNDEFINED = 0
    PLACE_POINT = 1
    PLACE_ROI = 2
    SEGMENTATION_EFFECT = 3


@dataclass
class ToolState:
    active_tool: ToolType = ToolType.UNDEFINED


class ToolUI(html.Div):
    def __init__(self, **kwargs):
        super().__init__(
            classes="tools-strip",
            **kwargs,
        )
        self._views_state = TypedState(self.state, ViewsState)
        self._typed_state = TypedState(self.state, ToolState)

        with self:
            Button(
                click=self.ctrl.reset,
                icon="mdi-camera-flip-outline",
                tooltip="Reset views",
            )
            self._build_tool_button(
                click=self._toggle_obliques_visibility,
                is_colored=self._views_state.name.are_obliques_visible,
                icon="mdi-cube-scan",
                tooltip=(f"{self._views_state.name.are_obliques_visible} ? 'Hide obliques' : 'Show obliques'",),
            )

            self._build_tool_button(
                click=lambda: self._activate_tool(ToolType.PLACE_POINT),
                is_colored=self._is_tool_active(ToolType.PLACE_POINT),
                icon="mdi-target",
                tooltip="Place point",
            )

            self._build_tool_button(
                click=lambda: self._activate_tool(ToolType.PLACE_ROI),
                is_colored=self._is_tool_active(ToolType.PLACE_ROI),
                icon="mdi-crop",
                tooltip="Place ROI",
            )

            self._build_tool_button(
                click=lambda: self._activate_tool(ToolType.SEGMENTATION_EFFECT),
                is_colored=self._is_tool_active(ToolType.SEGMENTATION_EFFECT),
                icon="mdi-shape",
                tooltip="Segmentation tool",
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

    def _build_tool_button(self, is_colored: str | None = None, **kwargs):
        Button(
            color=(f"{is_colored} && !{self._views_state.name.is_viewer_disabled} ? 'primary' : 'undefined'",)
            if is_colored
            else None,
            disabled=(self._views_state.name.is_viewer_disabled,),
            size="default",
            **kwargs,
        )

    def build_active_tool_ui(self):
        with html.Div():
            v3.VDivider(v_if=(f"!{self._is_tool_active(ToolType.UNDEFINED)}",))
            self.place_point_ui = PlacePointUI(v_if=(self._is_tool_active(ToolType.PLACE_POINT),))
            self.place_roi_ui = PlaceROIUI(v_if=(self._is_tool_active(ToolType.PLACE_ROI),))
            self.segmentation_effect_ui = SegmentationEffectUI(
                v_if=(self._is_tool_active(ToolType.SEGMENTATION_EFFECT),)
            )
