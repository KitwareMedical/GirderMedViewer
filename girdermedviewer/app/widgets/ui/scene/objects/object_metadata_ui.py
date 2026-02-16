from trame.widgets import html
from trame.widgets import vuetify3 as v3

from ....utils import Text


class SceneObjectMetadataUI(v3.VList):
    def __init__(self, obj_metadata: str, **kwargs):
        super().__init__(classes="metadata-list", **kwargs)
        self.metadata = obj_metadata
        self._build_ui()

    def _build_ui(self):
        with self:
            with (
                v3.VListItem(v_for=f"(value, key) in {self.metadata}.parent_meta", classes="metadata-item"),
                html.Div(classes="metadata-content"),
            ):
                Text("{{ key }}", classes="text-subtitle-2")
                Text("{{ value }}", classes="text-right text-body-2 metadata-ellipsis")

            v3.VDivider(
                v_if=(
                    f"Object.keys({self.metadata}.parent_meta).length > 0 && \
                        Object.keys({self.metadata}.meta).length > 0"
                )
            )

            with (
                v3.VListItem(v_for=f"(value, key) in {self.metadata}.meta", classes="metadata-item"),
                html.Div(classes="metadata-content"),
            ):
                Text("{{ key }}", classes="text-subtitle-2")
                Text("{{ value }}", classes="text-right text-body-2 metadata-ellipsis")
