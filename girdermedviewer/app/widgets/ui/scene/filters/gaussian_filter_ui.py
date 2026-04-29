from trame.widgets import html

from ....utils import Slider, Text


class GaussianSigmaSlider(Slider):
    def __init__(self, model: str, **kwargs):
        super().__init__(v_model=(model,), min=0, max=10, step=1, **kwargs)


class GaussianFilterUI(html.Div):
    def __init__(self, obj_filter_prop: str, **kwargs):
        super().__init__(**kwargs)
        self._filter_prop = obj_filter_prop
        self._build_ui()

    def _build_ui(self):
        with self:
            Text("Sigma", classes="text-header")
            GaussianSigmaSlider(model=f"{self._filter_prop}.sigma")
