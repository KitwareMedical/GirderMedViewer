import logging

from trame.widgets import html
from trame.widgets import vuetify3 as v3
from trame_server.utils.typed_state import TypedState

from ..views_ui import ViewsState
from .point_selector_ui import PointSelectorUI

logger = logging.getLogger(__name__)


class PlacePointUI(html.Div):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._typed_state = TypedState(self.state, ViewsState)
        self._build_ui()

    def _build_ui(self) -> None:
        with (
            self,
            v3.VCard(variant="flat", title="Place Point"),
            v3.VCardText(classes="tool-card"),
        ):
            PointSelectorUI(self._typed_state.get_sub_state(self._typed_state.name.position))
