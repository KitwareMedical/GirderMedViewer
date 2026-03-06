import logging

from trame.widgets import vuetify3 as v3
from trame_server.utils.typed_state import TypedState

from ...utils import Button
from .base_view import ViewState

logger = logging.getLogger(__name__)


class PositionMenu(Button):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._typed_state = TypedState(self.state, ViewState)
        self._build_ui()

    def _build_ui(self) -> None:
        with (
            self,
            v3.VMenu(
                v_model=(self._typed_state.name.is_position_menu_visible,),
                activator="parent",
                close_on_content_click=False,
                persistent=True,
                transition="slide-x-transition",
            ),
            v3.VCard(v_if=(self._typed_state.name.position,)),
            v3.VCardText(classes="d-flex justify-space-between align-center"),
        ):
            v3.VTextField(
                v_for=(
                    "(field, index) in \
                    [{ prefix: 'X', color: 'red' }, \
                    { prefix: 'Y', color: 'green' }, \
                    { prefix: 'Z', color: 'blue' }]",
                ),
                classes="mx-1 position-selector",
                model_value=(f"parseFloat({self._typed_state.name.position}[index]).toFixed(2)",),
                update_modelValue=(self.set_position, "[$event, index]"),
                prefix=("field.prefix",),
                color=("field.color",),
                type="number",
                density="compact",
            )

    def set_position(self, value: str, index: str) -> None:
        if value:
            old_position = list(self._typed_state.data.position)
            old_position[int(index)] = float(value)
            self._typed_state.data.position = tuple(old_position)
