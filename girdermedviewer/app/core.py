import os
from urllib.parse import urljoin
from configparser import ConfigParser

from trame.app import get_server
from trame.decorators import TrameApp, change, controller
from trame.widgets import gwc, html
from trame.ui.vuetify import SinglePageWithDrawerLayout

from trame.widgets.vuetify2 import (VContainer, VRow, VCol, VBtn, VCard, VIcon)

from .components import QuadView, ToolsStrip, update_location, handle_rowclick_on_file_manager

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
        # project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
        current_working_directory = os.getcwd()

        self.config = ConfigParser()
        config_file_path = os.path.join(current_working_directory, "app.cfg")
        self.config.read(config_file_path)

        self.state.api_url = urljoin(
            self.config.get("girder", "url"),
            self.config.get("girder", "api_root")
        )
        print(f'>>>>>>>>>>>> api_url {self.state.api_url}')

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
        self.state.clicked = []
        self.state.displayed = []
        self.state.detailed = []
        self.state.last_clicked = 0
        self.state.action_keys = [{"for": []}]

        self.ui = self._build_ui()


    @property
    def state(self):
        return self.server.state

    @property
    def ctrl(self):
        return self.server.controller

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
            layout.title.set_text(self.config.get("ui", "name"))
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
                    QuadView(v_if=("quad_view",))

            with layout.drawer:
                gwc.GirderFileManager(
                    v_if=("user",),
                    v_model=("clicked",),
                    location=("location",),
                    update_location=(update_location, "[$event]"),
                    rowclick=(
                        handle_rowclick_on_file_manager,
                        "[$event]"
                    ),
                )

                gwc.GirderDataDetails(
                    v_if=("detailed.length > 0",),
                    action_keys=("action_keys",),
                    value=("detailed",)
               )

            return layout
