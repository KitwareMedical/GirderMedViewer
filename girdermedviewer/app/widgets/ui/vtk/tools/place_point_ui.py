import logging
from dataclasses import dataclass, field

from trame.widgets import vuetify3 as v3
from trame_server.utils.typed_state import TypedState
from undo_stack import Signal

from .point_selector_ui import PointSelectorUI, PointState

logger = logging.getLogger(__name__)


@dataclass
class PlacePointState:
    position: PointState = field(default_factory=PointState)


class PlacePointUI(v3.VCard):
    position_updated = Signal()

    def __init__(self, **kwargs) -> None:
        super().__init__(classes="tool-card", title="Place Point", variant="flat", **kwargs)
        self._typed_state = TypedState(self.state, PlacePointState)
        self._build_ui()

    def _build_ui(self) -> None:
        with (
            self,
            v3.VCardText(),
        ):
            point_selector_ui = PointSelectorUI(self._typed_state.get_sub_state(self._typed_state.name.position))
            point_selector_ui.point_updated.connect(self.position_updated)
