from dataclasses import dataclass

from trame.widgets import html
from trame_server.utils.typed_state import TypedState
from undo_stack import Signal

from ....utils import NumberInput, Text


@dataclass
class PointState:
    pos_x: float | None = None
    pos_y: float | None = None
    pos_z: float | None = None


class PointSelectorUI(html.Div):
    point_updated = Signal()

    def __init__(self, point_position: TypedState[PointState], title: str | None = None, **kwargs) -> None:
        super().__init__(classes="point-selector")
        number_input_args = {"step": (0.1,), "precision": 2}
        number_input_args.update(kwargs)

        with self:
            if title is not None:
                Text(text=title, style="width: 30px")
            NumberInput(
                v_model=(point_position.name.pos_x,),
                base_color="red",
                classes="position-selector",
                color="red",
                prefix="X",
                update_modelValue=self.point_updated,
                **number_input_args,
            )
            NumberInput(
                v_model=(point_position.name.pos_y,),
                base_color="green",
                classes="position-selector",
                color="green",
                prefix="Y",
                update_modelValue=self.point_updated,
                **number_input_args,
            )
            NumberInput(
                v_model=(point_position.name.pos_z,),
                base_color="blue",
                classes="position-selector",
                color="blue",
                prefix="Z",
                update_modelValue=self.point_updated,
                **number_input_args,
            )
