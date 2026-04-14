import logging
from collections.abc import Callable

from trame.widgets import html
from trame.widgets import vuetify3 as v3
from trame_server.utils.typed_state import TypedState

from ..views_ui import ViewsState

logger = logging.getLogger(__name__)


class PointSelector(html.Div):
    def __init__(self, model_value: str, update_model_value: Callable, **kwargs) -> None:
        super().__init__(classes="point-selector")
        kwargs["model_value"] = (f"parseFloat({model_value}[axis]).toFixed(2)",)
        kwargs["update_modelValue"] = (update_model_value, "[$event, axis]")
        with self:
            v3.VTextField(
                v_for=(
                    "(field, axis) in \
                    [{ prefix: 'X', color: 'red' }, \
                    { prefix: 'Y', color: 'green' }, \
                    { prefix: 'Z', color: 'blue' }]",
                ),
                classes="mx-1 position-selector",
                prefix=("field.prefix",),
                base_color=("field.color",),
                type="number",
                density="compact",
                **kwargs,
            )


class PlacePointUI(html.Div):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._typed_state = TypedState(self.state, ViewsState)
        self._build_ui()

    def _build_ui(self) -> None:
        with (
            self,
            v3.VCard(v_if=(self._typed_state.name.position,), variant="flat", title="Place Point"),
            v3.VCardText(),
        ):
            PointSelector(
                model_value=self._typed_state.name.position,
                update_model_value=self.set_position,
            )

    def set_position(self, value: str, index: str) -> None:
        if value:
            old_position = list(self._typed_state.data.position)
            old_position[int(index)] = float(value)
            self._typed_state.data.position = tuple(old_position)
