import ast
import os
from urllib.parse import urljoin
from configparser import ConfigParser
from trame.app import get_server
from trame.decorators import TrameApp, change
from trame.widgets import gwc, html
from trame.ui.vuetify import SinglePageWithDrawerLayout
from trame.widgets.vuetify2 import (VContainer, VRow, VCol, VBtn, VCard, VIcon)
from .girder.components import GirderDrawer
from .vtk.components import QuadView, ToolsStrip
import xml.etree.ElementTree as ET

# ---------------------------------------------------------
# Engine class
# ---------------------------------------------------------


@TrameApp()
class MyTrameApp:
    def __init__(self, server=None):
        self.server = get_server(server, client_type="vue2")

        self.load_config()

        self.provider = gwc.GirderProvider(value=self.state.api_url, trame_server=self.server)
        self.ctrl.provider_logout = self.provider.logout

        self.state.trame__title = "GirderMedViewer"
        self.state.display_authentication = False
        self.state.obliques_visibility = True
        self.state.main_drawer = False
        self.state.user = None
        self.state.presets = self.get_presets()
        self.state.selected = []  # Items loaded and visible in the viewer
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

    def get_presets(self):
        #TODO: to adapt with last PR
        xml_file = "/home/justineantoine/KITWARE/PROJECTS/INRIA/GirderMedViewer/resources/presets.xml"
        tree = ET.parse(xml_file)
        root = tree.getroot()

        presets = [
            {
                "title": vp.get("name")
            } for vp in root.findall(".//VolumeProperty")
        ]
        return presets

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

        self.state.temp_dir = config.get("download", "directory", fallback=None)
        self.state.cache_mode = config.get("download", "cache_mode", fallback=None)
        self.state.date_format = config.get("ui", "date_format", fallback="%Y-%m-%d %H:%M:00")

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
            width="450px"
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
                    QuadView()

            with layout.drawer:
                GirderDrawer()

            return layout
