from trame.widgets import html

from ....utils import Text
from .object_components import PropertySlider


class OpacitySlider(PropertySlider):
    def __init__(self, **kwargs):
        super().__init__(min=0, max=1, step=0.1, **kwargs)


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
