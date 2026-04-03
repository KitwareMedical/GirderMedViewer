from trame.widgets import html
from trame_server.utils.typed_state import TypedState

from girdermedviewer.app.widgets.ui.vtk.tools.place_point_ui import PointSelectorUI

from ....utils import Button, Slider, Text
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

    def _build_ui(self):
        with self:
            Text("Center", classes="text-header")
            with PointSelectorUI(v_if=(self.center,), point_position=self.center):
                Button(
                    icon="mdi-star-four-points-outline",
                    tooltip="Use cursor",
                    click=f"{self.center} = [{self._views_state.name.position.pos_x}, {self._views_state.name.position.pos_y}, {self._views_state.name.position.pos_z}]",
                )
            Text("Radius", classes="text-header")
            Slider(disabled=(self._disabled,), v_model=(f"{self.radius}",))
