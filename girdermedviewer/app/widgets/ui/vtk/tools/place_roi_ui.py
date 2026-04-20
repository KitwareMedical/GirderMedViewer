import logging
from dataclasses import dataclass, field

from trame.widgets import vuetify3 as v3
from trame_server.utils.typed_state import TypedState
from undo_stack import Signal

from ....utils import Button
from .point_selector_ui import PointSelectorUI, PointState

logger = logging.getLogger(__name__)


@dataclass
class PlaceROIState:
    is_roi_locked: bool = False
    min_roi_bounds: PointState = field(default_factory=PointState)
    max_roi_bounds: PointState = field(default_factory=PointState)


class PlaceROIUI(v3.VCard):
    reset_clicked = Signal()

    def __init__(self, **kwargs) -> None:
        super().__init__(classes="tool-card", title="Place ROI", variant="flat", **kwargs)
        self._typed_state = TypedState(self.state, PlaceROIState)
        self._build_ui()

    def _build_ui(self) -> None:
        with (
            self,
            v3.VCardText(),
        ):
            with PointSelectorUI(
                self._typed_state.get_sub_state(self._typed_state.name.min_roi_bounds),
                title="Min",
                disabled=(self._typed_state.name.is_roi_locked,),
            ):
                Button(
                    active=(self._typed_state.name.is_roi_locked,),
                    click=self._toggle_roi_interaction,
                    icon="mdi-lock",
                    tooltip=(f"{self._typed_state.name.is_roi_locked} ? 'Unlock' : 'Lock'",),
                )
            with PointSelectorUI(
                self._typed_state.get_sub_state(self._typed_state.name.max_roi_bounds),
                title="Max",
                disabled=(self._typed_state.name.is_roi_locked,),
            ):
                Button(
                    click=self.reset_clicked,
                    disabled=(self._typed_state.name.is_roi_locked,),
                    icon="mdi-autorenew",
                    tooltip="Reset",
                )

    def _toggle_roi_interaction(self):
        self._typed_state.data.is_roi_locked = not self._typed_state.data.is_roi_locked
