from trame.widgets import html
from trame.widgets import vuetify3 as v3
from trame_server.utils.typed_state import TypedState

from ....utils import Button, Slider, Text
from ...point_selector_ui import PointSelectorUI
from ...vtk.views_ui import ViewsState


class StreamlineFilterUI(html.Div):
    def __init__(self, obj_filter_prop: str, disabled: str, **kwargs):
        super().__init__(**kwargs)
        self._obj_filter_prop = obj_filter_prop
        self._disabled = disabled

        self._views_state = TypedState(self.state, ViewsState)
        self._build_ui()

    @property
    def center(self) -> str:
        return f"{self._obj_filter_prop}.center"

    @property
    def radius(self) -> str:
        return f"{self._obj_filter_prop}.radius"

    @property
    def thickness(self) -> str:
        return f"{self._obj_filter_prop}.thickness"

    def _build_ui(self):
        with self:
            with html.Div(classes="display-property"):
                Text("Center", classes="text-header")
                with PointSelectorUI(v_if=(self.center,), point_position=self.center):
                    Button(
                        icon="mdi-star-four-points-outline",
                        tooltip="Use cursor",
                        click=f"{self.center} = [{self._views_state.name.position.pos_x}, {self._views_state.name.position.pos_y}, {self._views_state.name.position.pos_z}]",
                    )
            v3.VDivider(classes="display-property-divider")
            with html.Div(classes="display-property"):
                Text("Radius", classes="text-header")
                Slider(disabled=(self._disabled,), v_model=(f"{self.radius}",), min=0, max=50, step=(1,))
            v3.VDivider(classes="display-property-divider")
            with html.Div(classes="display-property"):
                Text("Thickness", classes="text-header")
                Slider(disabled=(self._disabled,), v_model=(f"{self.thickness}",), min=0, max=1, step=(0.1,))
