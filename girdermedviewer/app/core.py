import ast
import os
from urllib.parse import urljoin
from configparser import ConfigParser
import logging
import sys
from trame.app import get_server
from trame.decorators import TrameApp, change, controller
from trame.widgets import gwc, html
from trame.ui.vuetify import SinglePageWithDrawerLayout
from trame.widgets.vuetify2 import (VContainer, VRow, VCol, VBtn, VCard, VIcon)
from .girder.components import GirderDrawer
from .vtk.components import QuadView, ToolsStrip

# ---------------------------------------------------------
# Engine class
# ---------------------------------------------------------


@TrameApp()
class MyTrameApp:
    def __init__(self, server=None):
        self.server = get_server(server, client_type="vue2")

        self.load_config()
        self.configure_logs()

        self.provider = gwc.GirderProvider(value=self.state.api_url, trame_server=self.server)
        self.ctrl.provider_logout = self.provider.logout

        self.state.trame__title = "GirderMedViewer"
        self.state.display_authentication = False
        self.state.obliques_visibility = True
        self.state.main_drawer = False
        self.state.user = None
        self.state.file_loading_busy = False
        self.state.displayed = []  # Items loaded and visible in the viewer
        self.state.detailed = []  # Items for which detailed information is displayed
        self.state.last_clicked = 0
        self.state.action_keys = [{"for": []}]

        self.ui = self._build_ui()
        if self.server.hot_reload:
            self.server.controller.on_server_reload.add(self._build_ui)

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
        self.state.assetstore_dir = config.get("girder", "assetstore", fallback=None)
        self.state.app_name = config.get("ui", "name", fallback="Girder Medical Viewer")

        self.state.temp_dir = config.get("download", "directory", fallback=None)
        self.state.cache_mode = config.get("download", "cache_mode", fallback=None)

        self.log_level = config.get("logging", "log_level", fallback="INFO")

    def configure_logs(self):
        logging.basicConfig(stream=sys.stdout)
        # Silence dependencies logs and keep only the application ones
        logging.getLogger().setLevel(logging.WARNING)
        logging.getLogger(__package__).setLevel(self.log_level)

    @change("user")
    def set_user(self, user, **kwargs):
        self.state.first_name = user.get("firstName", None) if user else None
        self.state.last_name = user.get("lastName", None) if user else None
        self.state.display_authentication = user is None
        self.state.main_drawer = user is not None

    def _build_ui(self, *args, **kwargs):
        with SinglePageWithDrawerLayout(
            self.server,
            show_drawer=False,
            width="400px"
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
                    ToolsStrip()
                    qd = QuadView()
                    self.quad_view = qd

            with layout.drawer:
                GirderDrawer(self.quad_view)

            return layout
