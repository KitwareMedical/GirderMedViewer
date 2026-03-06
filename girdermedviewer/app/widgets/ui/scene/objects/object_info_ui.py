from trame.widgets import vuetify3 as v3


class SceneObjectInfoUI(v3.VList):
    def __init__(self, obj_info: str, **kwargs):
        super().__init__(dense=True, classes="pa-0", subheader=True, **kwargs)
        self.info = obj_info
        self._build_ui()

    def _build_ui(self):
        with self:
            v3.VListItem(
                "Size: {{ " + self.info + ".size}}",
                classes="py-1 body-2",
            )
            v3.VListItem(
                "Created on {{ " + self.info + ".created}}",
                classes="py-1 body-2",
            )
            v3.VListItem(
                "Updated on {{ " + self.info + ".updated}}",
                classes="py-1 body-2",
            )
