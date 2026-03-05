from trame.widgets import html

from ....utils import Text
from ..objects.object_components import PropertySlider


class GaussianSigmaSlider(PropertySlider):
    def __init__(self, model: str, **kwargs):
        super().__init__(v_model=(model,), min=0, max=10, step=1, thumb_label=True, **kwargs)


class GaussianFilterUI(html.Div):
    def __init__(self, obj_filter_prop: str, disabled: str, **kwargs):
        super().__init__(**kwargs)
        self._filter_prop = obj_filter_prop
        self._disabled = disabled
        self._build_ui()

    def _build_ui(self):
        with self:
            Text("Sigma", classes="text-header")
            GaussianSigmaSlider(disabled=(self._disabled,), model=f"{self._filter_prop}.sigma")
