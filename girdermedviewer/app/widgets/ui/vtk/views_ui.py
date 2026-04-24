import logging
from dataclasses import dataclass, field
from enum import Enum

from trame.widgets import html, rca
from trame.widgets import vuetify3 as v3
from trame_server.utils.typed_state import TypedState
from undo_stack import Signal

from ...utils import (
    Button,
    create_rendering_pipeline,
)
from ..point_selector_ui import PointState

logger = logging.getLogger(__name__)


class ViewType(Enum):
    SAGITTAL = "sag"
    THREED = "threed"
    CORONAL = "cor"
    AXIAL = "ax"


@dataclass
class SliderState:
    value: int | None = None
    min_value: int | None = None
    max_value: int | None = None


@dataclass
class ViewsState:
    position: PointState = field(default_factory=PointState)
    normals: tuple[tuple[float]] | None = None
    is_viewer_disabled: bool = True
    are_sliders_visible: bool = False
    are_obliques_visible: bool = False
    is_position_menu_visible: bool = False
    fullscreen: ViewType | None = None


@dataclass
class ViewState:
    slider_state: SliderState = field(default_factory=SliderState)


class ViewSliderUI(v3.VSlider):
    slice_updated = Signal(int)

    def __init__(self, typed_state: TypedState[SliderState], **kwargs):
        super().__init__(
            classes="slice-slider",
            hide_details=True,
            direction="vertical",
            height="100%",
            v_model=(typed_state.name.value,),
            min=(typed_state.name.min_value,),
            max=(typed_state.name.max_value,),
            step=1,
            update_modelValue=(self.slice_updated, f"[{typed_state.name.value}]"),
            **kwargs,
        )


class ViewUI(html.Div):
    def __init__(self, view_type: ViewType, **kwargs):
        super().__init__(**kwargs)

        self.renderer, self.render_window = create_rendering_pipeline()

        self.type = view_type
        self._views_state = TypedState(self.state, ViewsState)
        self._typed_state = TypedState(self.state, ViewState, namespace=view_type.value)

        self._build_ui()

    def update(self):
        self.view_handler.update()

    def _build_ui(self):
        with self:
            my_rca = rca.RemoteControlledArea(
                v_if=(f"!{self._views_state.name.is_viewer_disabled}",), display="image", send_mouse_move=True
            )
            self.view_handler = my_rca.create_view_handler(
                self.render_window,
                encoder="turbo-jpeg",
            )
            with html.Div(classes="view-gutter"), html.Div(classes="view-gutter-content"):
                Button(
                    click=self.toggle_fullscreen,
                    color="white",
                    disabled=(self._views_state.name.is_viewer_disabled,),
                    icon=(f"{self._views_state.name.fullscreen} == null ? 'mdi-fullscreen' : 'mdi-fullscreen-exit'",),
                    tooltip=(
                        f"{self._views_state.name.fullscreen} == null ? 'Extend to fullscreen' : 'Exit fullscreen'",
                    ),
                    variant="text",
                )
                if self.type != ViewType.THREED:
                    self.slider_ui = ViewSliderUI(
                        self._typed_state.get_sub_state(self._typed_state.name.slider_state),
                        v_if=(self._views_state.name.are_sliders_visible,),
                        disabled=(self._views_state.name.is_viewer_disabled,),
                    )

    def toggle_fullscreen(self):
        self._views_state.data.fullscreen = None if self._views_state.data.fullscreen else self.type


class ViewsUI(v3.VContainer):
    def __init__(self, **kwargs):
        super().__init__(classes="fill-height pa-0", fluid=True, **kwargs)
        self._typed_state = TypedState(self.state, ViewsState)
        self.view_uis: dict[ViewType, ViewUI] = {}

        self._build_quad_view()

    def _build_quad_view(self):
        with self, html.Div(classes="quad-view"):
            for view_type in [ViewType.SAGITTAL, ViewType.THREED, ViewType.CORONAL, ViewType.AXIAL]:
                self.view_uis[view_type] = ViewUI(
                    v_if=(self._has_view(view_type),),
                    classes=(f"{self._has_fullscreen_view(view_type)} ? 'fullscreen-view' : 'view'",),
                    view_type=view_type,
                )

    def _has_fullscreen_view(self, view_type: ViewType) -> str:
        return f"{self._typed_state.name.fullscreen} == '{view_type.value}'"

    def _has_view(self, view_type: ViewType) -> str:
        return f"{self._typed_state.name.fullscreen} == null || {self._has_fullscreen_view(view_type)}"
