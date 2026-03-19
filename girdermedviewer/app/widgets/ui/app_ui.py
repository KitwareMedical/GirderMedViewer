from dataclasses import dataclass

from trame.ui.vuetify3 import VAppLayout
from trame.widgets import gwc
from trame.widgets import vuetify3 as v3
from trame_server import Server
from trame_server.utils.typed_state import TypedState

from ..utils import AppConfig, GlobalStyle
from .girder.girder_browser_ui import GirderBrowserUI
from .girder.girder_connection_ui import GirderConnectionUI
from .scene.scene_ui import SceneUI
from .vtk.tool_strip_ui import ToolStripUI
from .vtk.views_ui import ViewsUI


@dataclass
class AppState:
    is_drawer_visible: bool = True
    is_viewer_disabled: bool = True
    is_browser_dialog_visible: bool = False


class AppLayout(VAppLayout):
    def __init__(
        self,
        server: Server,
        template_name: str = "main",
        app_name: str = "GirderMedViewer",
        **kwargs,
    ) -> None:
        super().__init__(server, template_name=template_name, **kwargs)
        self.state.trame__title = app_name
        self.typed_state = TypedState(self.state, AppState)

        with self:
            self.app_bar = v3.VAppBar(height=75)

            self.drawer = v3.VNavigationDrawer(
                v_model=(self.typed_state.name.is_drawer_visible,),
                classes="drawer",
                disable_resize_watcher=True,
                disable_route_watcher=True,
                permanent=True,
                width=500,
            )

            self.tool_strip = v3.VNavigationDrawer(
                permanent=True,
                width=50,
                disable_resize_watcher=True,
                disable_route_watcher=True,
            )

            self.viewer = v3.VMain(classes="d-flex flex-row flex-grow-1")


class AppUI:
    def __init__(self, layout: AppLayout, provider: gwc.GirderProvider, app_config: AppConfig) -> None:
        self.layout = layout
        self.provider = provider

        with self.layout:
            self.provider.register_layout(self.layout)
            GlobalStyle()
            with self.layout.app_bar:
                with v3.Template(v_slot_prepend=True):
                    self.girder_browser_ui = GirderBrowserUI()

                v3.VAppBarTitle(app_config.app_name, style="flex: 0 1 auto;")
                v3.VSpacer()
                self.girder_connection_ui = GirderConnectionUI()

            with self.layout.tool_strip:
                self.tool_strip_ui = ToolStripUI(disabled=self.name.is_viewer_disabled)

            with self.layout.viewer:
                self.views_ui = ViewsUI()

            with self.layout.drawer:
                self.scene_ui = SceneUI()

    @property
    def data(self) -> AppState:
        return self.layout.typed_state.data

    @property
    def name(self) -> AppState:
        return self.layout.typed_state.name
