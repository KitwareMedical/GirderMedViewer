import asyncio
from configparser import ConfigParser
from trame.app import get_server
from trame_server.utils.asynchronous import create_task
from trame.ui.vuetify import SinglePageWithDrawerLayout
from trame.widgets import gwc, html
from trame.widgets.vuetify2 import (VContainer, VRow, VCol,
                                    VBtn, VCard, VIcon)
from girder_client import GirderClient
from pathlib import Path
from tempfile import TemporaryDirectory
from vtkmodules.vtkCommonCore import vtkCollection
from slicer_trame.core import LayoutManager, SlicerApp
from slicer_trame.rca_view import register_rca_factories
from slicer_utils import (create_vertical_view_gutter_ui_vue2,
                          create_vertical_slice_view_gutter_ui_vue2)
from girder.models.file import File
from time import time

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

config = ConfigParser()
configFilePath = "C:\\Users\\Kitware\\Inria\\GirderMedViewer\\app.cfg"
config.read(configFilePath)

# -----------------------------------------------------------------------------
# Trame setup
# -----------------------------------------------------------------------------

server = get_server(client_type="vue2")
state, ctrl = server.state, server.controller
state.update({
    "api_url": "",
    "api_path": "",
    "display_authentication": False,
    "main_drawer": False,
    "user": None,
    "file_loading_busy": False,
    "current_layout_name": "Quad View",
    "clicked": [],
    "displayed": [],
    "last_clicked": 0,
    "action_keys": [{"for": []}],
})


# -----------------------------------------------------------------------------
# Girder configuration
# -----------------------------------------------------------------------------

api_url = config.get("girder", "url") + config.get("girder", "api_root")
CLIENT = GirderClient(apiUrl=api_url)
provider = gwc.GirderProvider(value=api_url, trame_server=server)
ctrl.provider_logout = provider.logout


# -----------------------------------------------------------------------------
# Data management
# -----------------------------------------------------------------------------

@state.change("user")
def set_user(user, **kwargs):
    if user:
        state.firstName = user.get("firstName", "").capitalize()
        state.lastName = user.get("lastName", "").upper()
        state.location = user
        state.display_authentication = False
        state.main_drawer = True
        CLIENT.setToken(state.token)
    else:
        remove_volume()
        state.display_authentication = True
        state.firstName = None
        state.lastName = None
        state.location = None
        if CLIENT:
            CLIENT.token = None
        state.main_drawer = False


def remove_volume():
    vol_nodes: vtkCollection = slicer_app.scene.GetNodesByClass(
        "vtkMRMLVolumeNode"
    )
    for i_vol in range(vol_nodes.GetNumberOfItems()):
        slicer_app.scene.RemoveNode(vol_nodes.GetItemAsObject(i_vol))

    state.displayed = []
    state.clicked = []


def create_load_task(item):
    state.file_loading_busy = True
    state.flush()

    async def load():
        await asyncio.sleep(1)
        try:
            load_files(item)
        finally:
            state.file_loading_busy = False
            state.flush()

    create_task(load())


def load_files(item):
    with TemporaryDirectory() as tmp_dir:
        file_list = []
        for file in CLIENT.listFile(item["_id"]):
            try:
                assetstore = File().getAssetstoreAdapter(file)
                file_list.append(assetstore.fullPath(file))
            except Exception:
                file_path = (Path(tmp_dir) / file["name"]).as_posix()
                CLIENT.downloadFile(
                    file["_id"],
                    file_path
                )
                file_list.append(file_path)

            volumes = slicer_app.io_manager.load_volumes(file_list)
            if not volumes:
                return

    # Show the largest volume
    def bounds_volume(v):
        b = [0] * 6
        v.GetImageData().GetBounds(b)
        return (b[1] - b[0]) * (b[3] - b[2]) * (b[5] - b[4])

    volumes = list(sorted(volumes, key=bounds_volume))
    slicer_app.display_manager.show_volume(
        volumes[-1],
        vr_preset="CT-Coronary-Arteries-3",
        do_reset_views=True,
    )


@state.change("location")
def update_clicked(location, **kwargs):
    if location:
        location_id = location.get("_id", "")
        if location_id and state.displayed:
            state.clicked = [item for item in state.displayed
                             if item["folderId"] == location_id]


def update_location(new_location):
    state.location = new_location


def handle_rowclick(row):
    if row.get('_modelType') == 'item':
        if time() - state.last_clicked > 1:
            if not state.displayed or state.displayed[0]["_id"] != row["_id"]:
                remove_volume()
                state.last_clicked = time()
                state.displayed = [row]
                state.clicked = [row]
                create_load_task(row)
            else:
                remove_volume()


# -----------------------------------------------------------------------------
# Viewer layout
# -----------------------------------------------------------------------------

slicer_app = SlicerApp()
register_rca_factories(
    slicer_app.view_manager,
    server,
    slice_view_ui_f=create_vertical_slice_view_gutter_ui_vue2,
    three_d_view_ui_f=create_vertical_view_gutter_ui_vue2,
)

layout_manager = LayoutManager(
    slicer_app.scene,
    slicer_app.view_manager,
    server.ui.layout_grid,
)
layout_manager.register_layout_dict(
    LayoutManager.default_grid_configuration()
)
layout_manager.set_layout(state.current_layout_name)


# -----------------------------------------------------------------------------
# App Layout
# -----------------------------------------------------------------------------
with SinglePageWithDrawerLayout(
    server,
    show_drawer=False,
    width="25%"
) as layout:
    provider.register_layout(layout)
    # TODO redo bar my self and put girder logo as nav bar icon,
    # and make it unclickable when not connected
    layout.title.set_text(config.get("girder", "name"))
    layout.toolbar.height = 75

    with layout.toolbar:
        with VBtn(
            fixed=True,
            right=True,
            large=True,
            click='display_authentication = !display_authentication'
        ):
            html.Div("{} {}".format(
                "{{ firstName }} ", "{{ lastName }} "), v_if=("user",)
            )
            html.Div("Log In", v_else=True)
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
                            "{{ firstName }} ", "{{ lastName }} "
                        ),
                        classes="subtitle-1 mb-1",
                    )
                with VCol(cols=2):
                    VBtn(
                        "Log Out",
                        click=ctrl.provider_logout,
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

        with VContainer(v_else=True, fluid=True, classes="fill-height pa-0"):
            server.ui.layout_grid(layout)

    with layout.drawer:
        gwc.GirderFileManager(
            v_if=("user",),
            v_model=("clicked",),
            location=("location",),
            update_location=(update_location, "[$event]"),
            rowclick=(
                handle_rowclick,
                "[$event]"
            ),
        )
        gwc.GirderDataDetails(
            v_if=("displayed.length > 0",),
            action_keys=("action_keys",),
            value=("displayed",),
        )

        with VContainer(v_if=("displayed.length > 0",)):
            VBtn(
                "Clear view",
                large=True,
                loading=("file_loading_busy",),
                click=remove_volume,
                style="margin-right: 20px"
            )


if __name__ == "__main__":
    server.start(port=8082)
