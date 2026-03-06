import logging

from trame.widgets import html
from trame.widgets import vuetify3 as v3
from trame_server.utils.typed_state import TypedState

from .base_view import ViewState
from .slice_view import SliceOrientation, SliceView
from .threed_view import ThreeDView

logger = logging.getLogger(__name__)


class ViewUI(v3.VContainer):
    def __init__(self, **kwargs):
        super().__init__(classes="fill-height pa-0", fluid=True, **kwargs)
        self._typed_state = TypedState(self.state, ViewState)
        self.views = []

        self._build_ui()
        self.ctrl.reset = self.reset
        self.ctrl.remove_data = self.remove_data

    @property
    def twod_views(self):
        return [view for view in self.views if isinstance(view, SliceView)]

    @property
    def threed_views(self):
        return [view for view in self.views if isinstance(view, ThreeDView)]

    def remove_data(self, data_id=None):
        for view in self.views:
            view.unregister_data(data_id)
        self.ctrl.view_update()

    def reset(self):
        for view in self.views:
            view.reset()
        self.ctrl.view_update()

    def _build_ui(self):
        with (
            self,
            html.Div(
                classes="quad-view",
            ),
        ):
            with SliceView(
                v_if=(self._has_view("sag_view"),),
                classes=(f"{self._has_fullscreen_view('sag_view')} ? 'fullscreen-view' : 'view'",),
                orientation=SliceOrientation.SAGITTAL,
                ref="sag_view",
            ) as sag_view:
                self.views.append(sag_view)

            with ThreeDView(
                v_if=(self._has_view("threed_view"),),
                classes=(f"{self._has_fullscreen_view('threed_view')} ? 'fullscreen-view' : 'view'",),
                ref="threed_view",
            ) as threed_view:
                self.views.append(threed_view)

            with SliceView(
                v_if=(self._has_view("cor_view"),),
                classes=(f"{self._has_fullscreen_view('cor_view')} ? 'fullscreen-view' : 'view'",),
                orientation=SliceOrientation.CORONAL,
                ref="cor_view",
            ) as cor_view:
                self.views.append(cor_view)

            with SliceView(
                v_if=(self._has_view("ax_view"),),
                classes=(f"{self._has_fullscreen_view('ax_view')} ? 'fullscreen-view' : 'view'",),
                orientation=SliceOrientation.AXIAL,
                ref="ax_view",
            ) as ax_view:
                self.views.append(ax_view)

    def _has_fullscreen_view(self, view_ref: str) -> str:
        return f"{self._typed_state.name.fullscreen} == '{view_ref}'"

    def _has_view(self, view_ref: str) -> str:
        return f"{self._typed_state.name.fullscreen} == null || {self._has_fullscreen_view(view_ref)}"
