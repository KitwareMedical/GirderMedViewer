import asyncio
from math import floor
import os
from time import time
from urllib.parse import urljoin

from configparser import ConfigParser
from girder_client import GirderClient

from tempfile import TemporaryDirectory
from trame_server.utils.asynchronous import create_task
from trame.app import get_server
from trame.ui.vuetify import SinglePageWithDrawerLayout
from trame.widgets import gwc, html, vtk
from trame.widgets.vuetify2 import (VContainer, VRow, VCol, VTooltip, Template,
                                    VBtn, VCard, VIcon)
from typing import Callable, Optional
from vtk import vtkNIFTIImageReader
from vtk_utils import create_rendering_pipeline, render_slices, render_3D

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
config = ConfigParser()
config_file_path = os.path.join(project_root, "app.cfg")
config.read(config_file_path)


# -----------------------------------------------------------------------------
# Trame setup
# -----------------------------------------------------------------------------

# Girder Web Components only supports Vue 2
server = get_server(client_type="vue2")
state, ctrl = server.state, server.controller
state.update({
    "display_authentication": False,
    "display_obliques": True,
    "main_drawer": False,
    "user": None,
    "file_loading_busy": False,
    "quad_view": True,
    "clicked": [],
    "displayed": [],
    "detailed": [],
    "last_clicked": 0,
    "action_keys": [{"for": []}],
})


# -----------------------------------------------------------------------------
# Girder configuration
# -----------------------------------------------------------------------------

api_url = urljoin(
    config.get("girder", "url"),
    config.get("girder", "api_root")
)

CLIENT = GirderClient(apiUrl=api_url)
provider = gwc.GirderProvider(value=api_url, trame_server=server)
ctrl.provider_logout = provider.logout


# -----------------------------------------------------------------------------
# Viewer layout
# -----------------------------------------------------------------------------

renderers, render_windows, interactors = create_rendering_pipeline(4)

# -----------------------------------------------------------------------------
# Data management
# -----------------------------------------------------------------------------


@state.change("user")
def set_user(user, **kwargs):
    if user:
        state.first_name = user.get("firstName", "")
        state.last_name = user.get("lastName", "")
        state.location = user
        state.display_authentication = False
        state.main_drawer = True
        CLIENT.setToken(state.token)
    else:
        remove_volume()
        state.first_name = None
        state.last_name = None
        state.location = None
        if CLIENT:
            CLIENT.token = None
        state.main_drawer = False


@state.change("location")
def on_location_changed(location, **kwargs):
    if location:
        location_id = location.get("_id", "")
        if location_id:
            if state.displayed:
                state.clicked = [
                    item for item in state.displayed
                    if item["folderId"] == location_id
                ]
            state.detailed = state.clicked if state.clicked else [location]
        else:
            state.detailed = []


def remove_volume():
    for view in range(4):
        renderers[view].RemoveAllViewProps()
        renderers[view].ResetCameraClippingRange()
        render_windows[view].Render()
        interactors[view].Render()

    ctrl.view_update()

    state.displayed = []
    state.clicked = []
    state.detailed = (
        [state.location] if state.location and
        state.location.get("_id", "") else []
    )


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


def load_file(file_path):
    if file_path.endswith((".nii", ".nii.gz")):
        reader = vtkNIFTIImageReader()
        reader.SetFileName(file_path)
        reader.Update()
        return reader.GetOutput()

    # TODO Handle dicom, vti, mesh

    raise Exception("File format is not handled for {}".format(file_path))


def load_files(item):
    with TemporaryDirectory() as tmp_dir:
        file_list = []
        for file in CLIENT.listFile(item["_id"]):
            file_path = os.path.join(tmp_dir, file["name"])
            CLIENT.downloadFile(
                file["_id"],
                file_path
            )
            file_list.append(file_path)

        if len(file_list) > 1:
            raise Exception(
                "You are trying to load more than one file. \
                If so, please load a compressed archive."
            )

        image_data = load_file(file_list[0])

    render_slices(
        image_data,
        renderers[:3],
        render_windows[:3],
        interactors[:3],
        obliques=state.display_obliques
    )

    render_3D(
        image_data,
        renderers[3],
        render_windows[3]
    )

    ctrl.view_update()


def update_location(new_location):
    state.location = new_location


def handle_rowclick_on_file_manager(row):
    if row.get('_modelType') == 'item':
        # Ignore double click on item
        if time() - state.last_clicked > 1:
            if not state.displayed or state.displayed[0]["_id"] != row["_id"]:
                remove_volume()
                state.last_clicked = time()
                state.displayed = [row]
                state.detailed = [row]
                state.clicked = [row]
                create_load_task(row)
            else:
                remove_volume()


def hide_obliques():
    state.display_obliques = False
    for view in range(3):
        for axis in range(3):
            render_windows[view].cursor_rep.GetResliceCursorActor() \
                .GetCenterlineProperty(axis) \
                .SetOpacity(0.0)
        render_windows[view].reslice_image.GetResliceCursorWidget() \
            .ProcessEventsOff()
        renderers[view].ResetCameraClippingRange()
        render_windows[view].Render()
        interactors[view].Render()

    ctrl.view_update()


def show_obliques():
    state.display_obliques = True
    for view in range(3):
        for axis in range(3):
            render_windows[view].cursor_rep.GetResliceCursorActor() \
                .GetCenterlineProperty(axis) \
                .SetOpacity(1.0)
        render_windows[view].reslice_image.GetResliceCursorWidget() \
            .ProcessEventsOn()
        renderers[view].ResetCameraClippingRange()
        render_windows[view].Render()
        interactors[view].Render()

    ctrl.view_update()


# -----------------------------------------------------------------------------
# Layout
# -----------------------------------------------------------------------------


class Button():
    def __init__(
        self,
        *,
        tooltip: str,
        icon: str,
        icon_color: str = None,
        click: Optional[Callable] = None,
        size: int = 40,
        **kwargs,
    ) -> None:

        with VTooltip(
            tooltip,
            right=True,
            transition="slide-x-transition"
        ):
            with Template(v_slot_activator="{ on, attrs }"):
                with VBtn(
                    text=True,
                    rounded=0,
                    height=size,
                    width=size,
                    min_height=size,
                    min_width=size,
                    click=click,
                    v_bind="attrs",
                    v_on="on",
                    **kwargs,
                ):
                    VIcon(icon, size=floor(0.6 * size), color=icon_color)


class ToolsStrip(html.Div):
    def __init__(self, **kwargs):
        super().__init__(
            classes="bg-grey-darken-4 d-flex flex-column align-center",
            **kwargs,
        )

        with self:
            with html.Div(v_if=("display_obliques",),):
                Button(
                    tooltip="Hide obliques",
                    icon="mdi-eye-remove-outline",
                    click=hide_obliques,
                    disabled=("displayed.length === 0",)
                )

            with html.Div(v_else=True):
                Button(
                    tooltip="Show obliques",
                    icon="mdi-eye-outline",
                    click=show_obliques,
                    disabled=("displayed.length === 0",),
                )

            Button(
                tooltip="Clear View",
                icon="mdi-reload",
                click=remove_volume,
                loading=("file_loading_busy",),
                disabled=("displayed.length === 0",)
            )


class ViewGutter(html.Div):
    def __init__(self, view=0):
        super().__init__(
            classes="gutter",
            style=(
                "position: absolute;"
                "top: 0;"
                "left: 0;"
                "background-color: transparent;"
                "height: 100%;"
            )
        )
        self.view = view
        with self:
            with html.Div(
                v_if=("displayed.length>0",),
                classes="gutter-content d-flex flex-column fill-height pa-2"
            ):
                Button(
                    tooltip="Reset View",
                    icon="mdi-camera-flip-outline",
                    icon_color="white",
                    click=self.reset_view,
                )

                Button(
                    v_if=("quad_view",),
                    tooltip="Extend to fullscreen",
                    icon="mdi-fullscreen",
                    icon_color="white",
                    click=self.extend_fullscreen,
                )

                Button(
                    v_else=True,
                    tooltip="Exit fullscreen",
                    icon="mdi-fullscreen-exit",
                    icon_color="white",
                    click=self.exit_fullscreen,
                )

    def reset_view(self):
        reslice_image = render_windows[self.view].reslice_image
        if reslice_image:
            bounds = renderers[self.view].GetViewProps() \
                .GetLastProp() \
                .GetBounds()
            center = (
                (bounds[0] + bounds[1]) / 2.0,
                (bounds[2] + bounds[3]) / 2.0,
                (bounds[4] + bounds[5]) / 2.0
            )
            # Replace slice cursor at the volume center
            reslice_image.GetResliceCursor().SetCenter(center)
            reslice_image.GetResliceCursorWidget().ResetResliceCursor()
        else:
            renderers[self.view].GetActiveCamera().SetFocalPoint((0, 0, 0))
            renderers[self.view].GetActiveCamera().SetPosition((0, 0, 1))

        renderers[self.view].ResetCameraScreenSpace(0.8)
        render_windows[self.view].Render()
        interactors[self.view].Render()

        ctrl.view_update()

    def extend_fullscreen(self):
        state.quad_view = False

    def exit_fullscreen(self):
        state.quad_view = True


class QuadView(VContainer):
    def __init__(self, **kwargs):
        super().__init__(
            classes="fill-height pa-0",
            **kwargs
        )

        with self:
            with VRow(style="height:50%", no_gutters=True):
                with VCol(cols=6):
                    with vtk.VtkRemoteView(render_windows[0]) as sag_view:
                        ViewGutter(0)
                        ctrl.view_update.add(sag_view.update)
                        ctrl.view_reset_camera.add(sag_view.reset_camera)
                with VCol(cols=6):
                    with vtk.VtkRemoteView(render_windows[3]) as threed_view:
                        ViewGutter(3)
                        ctrl.view_update.add(threed_view.update)
                        ctrl.view_reset_camera.add(threed_view.reset_camera)

            with VRow(style="height:50%", no_gutters=True):
                with VCol(cols=6):
                    with vtk.VtkRemoteView(render_windows[1]) as cor_view:
                        ViewGutter(1)
                        ctrl.view_update.add(cor_view.update)
                        ctrl.view_reset_camera.add(cor_view.reset_camera)
                with VCol(cols=6):
                    with vtk.VtkRemoteView(render_windows[2]) as ax_view:
                        ViewGutter(2)
                        ctrl.view_update.add(ax_view.update)
                        ctrl.view_reset_camera.add(ax_view.reset_camera)


with SinglePageWithDrawerLayout(
    server,
    show_drawer=False,
    width="25%"
) as layout:
    provider.register_layout(layout)
    layout.title.set_text(config.get("ui", "name"))
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


if __name__ == "__main__":
    server.start()
