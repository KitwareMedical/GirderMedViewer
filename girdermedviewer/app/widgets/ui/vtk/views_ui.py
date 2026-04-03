import logging

from trame.widgets import html, vtk
from trame.widgets import vuetify3 as v3
from trame_server.utils.typed_state import TypedState
from undo_stack import Signal

from ...utils import (
    Button,
    create_rendering_pipeline,
)
from .views_state import SliderState, ViewsState, ViewState, ViewType

logger = logging.getLogger(__name__)


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


class ViewUI(vtk.VtkRemoteView):
    def __init__(self, view_type: ViewType, **kwargs):
        renderer, render_window = create_rendering_pipeline()
        super().__init__(
            render_window,
            interactive_quality=80,
            interactive_ratio=1,
            id=view_type.value,
            ref=view_type.value,  # avoids recreating a view when UI is rebuilt
            **kwargs,
        )
        self.renderer = renderer
        self.type = view_type
        self._views_state = TypedState(self.state, ViewsState)
        self._typed_state = TypedState(self.state, ViewState, namespace=view_type.value)

        self.ctrl.start_animation.add(self.start_animation)
        self.ctrl.stop_animation.add(self.stop_animation)

        self._build_ui()

    def _build_ui(self):
        with self, html.Div(classes="view-gutter"), html.Div(classes="view-gutter-content"):
            Button(
                click=self.toggle_fullscreen,
                color="white",
                icon=(f"{self._views_state.name.fullscreen} == null ? 'mdi-fullscreen' : 'mdi-fullscreen-exit'",),
                tooltip=(f"{self._views_state.name.fullscreen} == null ? 'Extend to fullscreen' : 'Exit fullscreen'",),
                variant="text",
            )
            if self.type != ViewType.THREED:
                self.slider_ui = ViewSliderUI(
                    self._typed_state.get_sub_state(self._typed_state.name.slider_state),
                    v_if=(self._views_state.name.are_sliders_visible,),
                    start=self.ctrl.start_animation,
                    end=self.ctrl.stop_animation,
                )

    def toggle_fullscreen(self):
        self._views_state.data.fullscreen = None if self._views_state.data.fullscreen else self.type


class ViewsUI(v3.VContainer):
    def __init__(self, **kwargs):
        super().__init__(classes="fill-height pa-0", fluid=True, **kwargs)
        self._typed_state = TypedState(self.state, ViewsState)
        self.view_uis: dict[ViewType, ViewUI] = {}

        self._build_quad_view()

    def update_views(self):
        for view_ui in self.view_uis.values():
            view_ui.update()

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
