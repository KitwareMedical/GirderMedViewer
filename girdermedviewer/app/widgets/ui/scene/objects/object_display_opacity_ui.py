from trame.widgets import html
from trame.widgets import vuetify3 as v3

from ....utils import Text


class OpacitySlider(v3.VSlider):
    def __init__(self, **kwargs):
        super().__init__(min=0.001, max=0.999, step=1e-3, hide_details=True, **kwargs)


class ObjectDisplayOpacityUI(html.Div):
    def __init__(self, obj_display: str, **kwargs):
        super().__init__(
            classes="display-property",
            **kwargs,
        )
        self.display = obj_display
        self._build_ui()

    def _build_ui(self):
        with self:
            Text("Opacity", classes="text-header")
            OpacitySlider(v_model=(f"{self.display}.opacity",))
