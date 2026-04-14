import logging
from collections.abc import Callable
from dataclasses import dataclass

from trame.widgets import html
from trame.widgets import vuetify3 as v3
from trame_server.utils.typed_state import TypedState
from undo_stack import Signal

from ....utils import Button, Text

logger = logging.getLogger(__name__)


@dataclass
class PlaceROIState:
    is_roi_locked: bool = False
    roi_bounds: tuple[float] = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)


class BoundSelector(html.Div):
    def __init__(self, model_value: str, update_model_value: Callable, max: bool = False, **kwargs) -> None:
        super().__init__(classes="point-selector")
        axis = "2 * axis" + (" + 1" if max else "")
        kwargs["model_value"] = (f"parseFloat({model_value}[{axis}]).toFixed(2)",)
        kwargs["update_modelValue"] = (update_model_value, f"[$event, {axis}]")
        with self:
            Text(text="Max" if max else "Min")
            v3.VTextField(
                v_for=(
                    "(field, axis) in \
                    [{ prefix: 'X', color: 'red'  }, \
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


class PlaceROIUI(html.Div):
    reset_clicked = Signal()

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._typed_state = TypedState(self.state, PlaceROIState)
        self._build_ui()

    def _build_ui(self) -> None:
        with (
            self,
            v3.VCard(variant="flat", title="Place ROI"),
            v3.VCardText(),
        ):
            with BoundSelector(
                model_value=self._typed_state.name.roi_bounds,
                update_model_value=self.set_bounds,
                disabled=(self._typed_state.name.is_roi_locked,),
            ):
                Button(
                    active=(self._typed_state.name.is_roi_locked,),
                    click=self._toggle_roi_interaction,
                    icon="mdi-lock",
                    tooltip=(f"{self._typed_state.name.is_roi_locked} ? 'Unlock' : 'Lock'",),
                )
            with BoundSelector(
                model_value=self._typed_state.name.roi_bounds,
                update_model_value=self.set_bounds,
                max=True,
                disabled=(self._typed_state.name.is_roi_locked,),
            ):
                Button(
                    click=self.reset_clicked,
                    disabled=(self._typed_state.name.is_roi_locked,),
                    icon="mdi-autorenew",
                )

    def _toggle_roi_interaction(self):
        self._typed_state.data.is_roi_locked = not self._typed_state.data.is_roi_locked

    def set_bounds(self, value: str, index: str) -> None:
        if value:
            old_position = list(self._typed_state.data.roi_bounds)
            old_position[int(index)] = float(value)
            self._typed_state.data.roi_bounds = tuple(old_position)
