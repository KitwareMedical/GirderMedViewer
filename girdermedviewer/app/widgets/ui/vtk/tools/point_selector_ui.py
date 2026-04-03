from dataclasses import dataclass

from trame.widgets import html
from trame_server.utils.typed_state import TypedState

from ....utils import NumberInput, Text


@dataclass
class PointState:
    pos_x: float | None = None
    pos_y: float | None = None
    pos_z: float | None = None


class PointSelectorUI(html.Div):
    def __init__(self, point_position: TypedState[PointState], title: str | None = None, **kwargs) -> None:
        super().__init__(classes="point-selector")
        number_input_args = {"step": (0.1,), "precision": 2}
        number_input_args.update(kwargs)

        with self:
            if title is not None:
                Text(text=title, style="width: 30px")
            NumberInput(
                v_model=(point_position.name.pos_x,),
                classes="position-selector",
                prefix="X",
                base_color="red",
                color="red",
                **number_input_args,
            )
            NumberInput(
                v_model=(point_position.name.pos_y,),
                classes="position-selector",
                prefix="Y",
                base_color="green",
                color="green",
                **number_input_args,
            )
            NumberInput(
                v_model=(point_position.name.pos_z,),
                classes="position-selector",
                prefix="Z",
                base_color="blue",
                color="blue",
                **number_input_args,
            )
