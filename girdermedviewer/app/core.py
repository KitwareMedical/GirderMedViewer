import ast
import os
from urllib.parse import urljoin
from configparser import ConfigParser

from trame.app import get_server
from trame.decorators import TrameApp, change, controller
from trame.widgets import gwc, html
from trame.ui.vuetify import SinglePageWithDrawerLayout

from trame.widgets.vuetify2 import (VContainer, VRow, VCol, VBtn, VCard, VIcon)

from .components import QuadView, ToolsStrip, GirderFileSelector

from trame.widgets import vuetify, vtk
#from trame.widgets import vuetify3, vtk
# from trame.ui.vuetify import SinglePageLayout

# ---------------------------------------------------------
# Engine class
# ---------------------------------------------------------

@TrameApp()
class MyTrameApp:
    def __init__(self, server=None):
        self.server = get_server(server, client_type="vue2")
        if self.server.hot_reload:
            self.server.controller.on_server_reload.add(self._build_ui)

        self.load_config()

        self.provider = gwc.GirderProvider(value=self.state.api_url, trame_server=self.server)
        self.ctrl.provider_logout = self.provider.logout

        # Set state variable
        self.state.trame__title = "GirderMedViewer"
        self.state.resolution = 6
        self.state.display_authentication= False
        self.state.display_obliques = True
        self.state.main_drawer = False
        self.state.user = None
        self.state.file_loading_busy = False
        self.state.quad_view = True
        self.state.selected = [] # FIXME: explain the role of this variable
        self.state.displayed = [] # FIXME: explain the role of this variable
        self.state.detailed = [] # FIXME: explain the role of this variable
        self.state.last_clicked = 0
        self.state.action_keys = [{"for": []}]

        self.quad_view = None
        self.ui = self._build_ui()


    @property
    def state(self):
        return self.server.state

    @property
    def ctrl(self):
        return self.server.controller

    def load_config(self, config_file_path=None):
        """
        Load the configuration file app.cfg if any and set the state variables accordingly.
        If provided, app.cfg must at least contain girder/url and girder/api_root.
        """
        if config_file_path is None:
            current_working_directory = os.getcwd()
            config_file_path = os.path.join(current_working_directory, "app.cfg")

        if os.path.exists(config_file_path) is False:
            return

        config = ConfigParser()
        config.read(config_file_path)

        self.state.api_url = urljoin(
            config.get("girder", "url"),
            config.get("girder", "api_root")
        )
        self.state.default_location = ast.literal_eval(
            config.get("girder", "default_location", fallback="{}"))
        self.state.app_name = config.get("ui", "name", fallback="Girder Medical Viewer")

    @controller.set("reset_resolution")
    def reset_resolution(self):
        self.state.resolution = 6

    @change("resolution")
    def on_resolution_change(self, resolution, **kwargs):
        print(f">>> ENGINE(a): Slider updating resolution to {resolution}")

    def _build_ui(self, *args, **kwargs):
        with SinglePageWithDrawerLayout(
                self.server,
                show_drawer=False,
                width="25%"
            ) as layout:
            self.provider.register_layout(layout)
            layout.title.set_text(self.state.app_name)
            layout.toolbar.height = 75

            with layout.toolbar:
                with VBtn(
                    fixed=True,
                    right=True,
                    large=True,
                    click='display_authentication = !display_authentication'
                ):
                    html.Span(
                        "{} {}".format("{{ first_name }} ", "{{ last_name }} "),
                        v_if=("user",)
                    )
                    html.Span("Log In", v_else=True)
                    VIcon("mdi-account", v_if=("user",))
                    VIcon("mdi-login-variant", v_else=True)

            with layout.content:
                with VContainer(
                    v_if=("display_authentication",)
                ), VCard():
                    gwc.GirderAuthentication(v_if=("!user",), register=False)

                    with VRow(v_else=True):
                        with VCol(cols=8):
                            html.Div(
                                "Welcome {} {}".format(
                                    "{{ first_name }} ", "{{ last_name }} "
                                ),
                                classes="subtitle-1 mb-1",
                            )
                        with VCol(cols=2):
                            VBtn(
                                "Log Out",
                                click=self.ctrl.provider_logout,
                                block=True,
                                color="primary",
                            )
                        with VCol(cols=2):
                            VBtn(
                                "Go to Viewer",
                                click='display_authentication = false',
                                block=True,
                                color="primary",
                            )

                with html.Div(
                    v_else=True,
                    fluid=True,
                    classes="fill-height d-flex flex-row flex-grow-1"
                ):
                    ts = ToolsStrip()
                    qd = QuadView(v_if=("quad_view",))
                    self.quad_view = qd
                    ts.set_quad_view(qd)

            with layout.drawer:
                GirderFileSelector(self.quad_view)

                gwc.GirderDataDetails(
                    v_if=("detailed.length > 0",),
                    action_keys=("action_keys",),
                    value=("detailed",)
               )

            return layout
