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
    def __init__(self, point_position: TypedState[PointState] | str, title: str | None = None, **kwargs) -> None:
        super().__init__(classes="point-selector")
        self._point_position = point_position
        number_input_args = {"step": (0.1,), "precision": 2}
        number_input_args.update(kwargs)

        with self:
            if title is not None:
                Text(text=title, style="width: 30px")
            NumberInput(
                v_model=(self.point_position[0],),
                classes="position-selector",
                prefix="X",
                base_color="red",
                color="red",
                **number_input_args,
            )
            NumberInput(
                v_model=(self.point_position[1],),
                classes="position-selector",
                prefix="Y",
                base_color="green",
                color="green",
                **number_input_args,
            )
            NumberInput(
                v_model=(self.point_position[2],),
                classes="position-selector",
                prefix="Z",
                base_color="blue",
                color="blue",
                **number_input_args,
            )

    @property
    def point_position(self) -> list[str]:
        if isinstance(self._point_position, TypedState):
            return [self._point_position.name.pos_x, self._point_position.name.pos_y, self._point_position.name.pos_z]
        return [f"{self._point_position}[0]", f"{self._point_position}[1]", f"{self._point_position}[2]"]
