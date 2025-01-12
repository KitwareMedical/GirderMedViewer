import asyncio
from math import floor
import logging
import os
import sys
from time import time

from tempfile import TemporaryDirectory
from trame_server.utils.asynchronous import create_task
from trame.app import get_server
from trame.widgets import gwc, html, vtk
from trame.widgets.vuetify2 import (VContainer, VRow, VCol, VTooltip, Template,
                                    VBtn, VCard, VIcon)
from typing import Callable, Optional
from .vtk_utils import create_rendering_pipeline, render_slice, render_3D, load_file
from vtk import (
    vtkResliceCursorLineRepresentation,
)

from girder_client import GirderClient

logging.basicConfig(stream=sys.stdout)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

server = get_server(client_type="vue2")
state, ctrl = server.state, server.controller


# -----------------------------------------------------------------------------
# Viewer layout
# -----------------------------------------------------------------------------

quad_view = None

girder_client = GirderClient(apiUrl=state.api_url)



class GirderFileSelector(gwc.GirderFileManager):
    def __init__(self, quad_view, **kwargs):
        super().__init__(
            v_if=("user",),
            v_model=("selected",),
            location=("location",),
            update_location=(self.update_location, "[$event]"),
            rowclick=(
                self.handle_rowclick_on_file_manager,
                "[$event]"
            ),
            **kwargs
        )
        self.quad_view = quad_view

    def handle_rowclick_on_file_manager(self, row):
        if row.get('_modelType') == 'item':
            # Ignore double click on item
            if time() - state.last_clicked > 1:
                if not state.displayed or state.displayed[0]["_id"] != row["_id"]:
                    self.quad_view.remove_volume()
                    state.last_clicked = time()
                    state.displayed = [row]
                    state.detailed = [row]
                    state.selected = [row]
                    self.create_load_task(row)
                else:
                    self.quad_view.remove_volume()
    
    def update_location(self, new_location):
        """
        Called each time the user browse through the GirderFileManager.
        """
        logger.debug(f"Updating location to {new_location}")
        state.location = new_location

    def create_load_task(self, item):
        logger.debug(f"Creating load task for {item}")
        state.file_loading_busy = True
        state.flush()

        async def load():
            logger.debug(f"Wait and load")
            await asyncio.sleep(1)
            try:
                quad_view.load_files(item)
            finally:
                state.file_loading_busy = False
                state.flush()

        create_task(load())

    @state.change("location")
    def on_location_changed(location, **kwargs):
        logger.debug(f"Location changed to {location}")
        if location:
            location_id = location.get("_id", "")
            if location_id:
                if state.displayed:
                    state.selected = [
                        item for item in state.displayed
                        if item["folderId"] == location_id
                    ]
                state.detailed = state.selected if state.selected else [location]
            else:
                state.detailed = []

    @state.change("api_url")
    def set_api_url(api_url, **kwargs):
        # FIXME make girder_client a member variable
        global girder_client
        logger.debug(f"Setting api_url to {api_url}")
        girder_client = GirderClient(apiUrl=api_url)

    @state.change("user")
    def set_user(user, **kwargs):
        logger.debug(f"Setting user to {user}")
        if user:
            state.first_name = user.get("firstName", "")
            state.last_name = user.get("lastName", "")
            state.location = state.default_location or user
            state.display_authentication = False
            state.main_drawer = True
            girder_client.setToken(state.token)
        else:
            quad_view.remove_volume()
            state.first_name = None
            state.last_name = None
            state.location = None
            if girder_client:
                girder_client.token = None
            state.main_drawer = False

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
    def __init__(self, quad_view = None, **kwargs):
        super().__init__(
            classes="bg-grey-darken-4 d-flex flex-column align-center",
            **kwargs,
        )
        self.quad_view = quad_view

        with self:
            with html.Div(v_if=("display_obliques",),):
                Button(
                    tooltip="Hide obliques",
                    icon="mdi-eye-remove-outline",
                    click=lambda: self.quad_view.set_obliques_visibility(False),
                    disabled=("displayed.length === 0",)
                )

            with html.Div(v_else=True):
                Button(
                    tooltip="Show obliques",
                    icon="mdi-eye-outline",
                    click=lambda: self.quad_view.set_obliques_visibility(True),
                    disabled=("displayed.length === 0",),
                )

            Button(
                tooltip="Clear View",
                icon="mdi-reload",
                click=lambda: self.quad_view.remove_volume(),
                loading=("file_loading_busy",),
                disabled=("displayed.length === 0",)
            )

    def set_quad_view(self, quad_view):
        self.quad_view = quad_view

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
        reslice_image = self.view.render_window.reslice_image
        if reslice_image:
            bounds = self.view.renderer.GetViewProps() \
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
            self.view.renderer.GetActiveCamera().SetFocalPoint((0, 0, 0))
            self.view.renderer.GetActiveCamera().SetPosition((0, 0, 1))

        self.view.renderer.ResetCameraScreenSpace(0.8)
        self.view.render_window.Render()
        self.view.interactors.Render()

        ctrl.view_update()

    def extend_fullscreen(self):
        state.quad_view = False

    def exit_fullscreen(self):
        state.quad_view = True


class VtkView(vtk.VtkRemoteView):
    """ Base class for VTK views """
    def __init__(self, **kwargs):
        renderers, render_windows, interactors = create_rendering_pipeline(1)
        super().__init__(render_windows[0], **kwargs)
        self.renderer = renderers[0]
        self.render_window = render_windows[0]
        self.interactor = interactors[0]

    def remove_volume(self):
        self.renderer.RemoveAllViewProps()
        self.renderer.ResetCameraClippingRange()
        self.render_window.Render()
        self.interactor.Render()


class SliceView(VtkView):
    """ Display volume as a 2D slice along a given axis """
    def __init__(self, axis, **kwargs):
        super().__init__(**kwargs)
        self.axis = axis
        self.reslice_image_viewers = []
        self._build_ui()
    
    def add_volume(self, image_data):
        reslice_image_viewer = render_slice(
            image_data,
            self.renderer,
            self.axis,
            obliques=state.display_obliques
        )
        self.reslice_image_viewers.append(reslice_image_viewer)

    def get_reslice_cursor_actor(self):
        return self.get_reslice_cursor_representation().GetResliceCursorActor()

    def get_reslice_cursor_representation(self):
        return vtkResliceCursorLineRepresentation.SafeDownCast(
            self.get_reslice_cursor_widget().GetRepresentation())

    def get_reslice_cursor_widget(self):
        return self.reslice_image_viewers[0].GetResliceCursorWidget()

    def set_obliques_visibility(self, visible):
        for axis in range(3):
            self.get_reslice_cursor_actor.GetCenterlineProperty(axis) \
                .SetOpacity(1.0 if visible else 0.0)
        self.get_reslice_cursor_widget.SetProcessEvents(visible)
        # self.renderer.ResetCameraClippingRange()
        # self.render_window.Render()
        self.interactor.Render()

    def _build_ui(self):
        with self:
            ViewGutter(self)
            ctrl.view_update.add(self.update)
            ctrl.view_reset_camera.add(self.reset_camera)


class ThreeDView(VtkView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._build_ui()
    
    def add_volume(self, image_data):
        render_3D(
            image_data,
            self.renderer
        )
    def _build_ui(self):
        with self:
            ViewGutter(self)
            ctrl.view_update.add(self.update)
            ctrl.view_reset_camera.add(self.reset_camera)


class QuadView(VContainer):
    def __init__(self, **kwargs):
        super().__init__(
            classes="fill-height pa-0",
            **kwargs
        )
        self.twod_views = []
        self.threed_views = []
        self.views = []
        self._build_ui()

        global quad_view
        quad_view = self

    # FIXME split VTK from Girder
    def remove_volume(self):
        for view in self.views:
            view.remove_volume()

        # FIXME
        # ctrl.view_update()

        state.displayed = []
        state.selected = []
        state.detailed = (
            [state.location] if state.location and
            state.location.get("_id", "") else []
        )

    # FIXME split VTK from Girder
    def load_files(self, item):
        logger.debug(f"Loading files {item}")
        with TemporaryDirectory() as tmp_dir:
            file_list = []
            logger.debug(f"Listing files")
            for file in girder_client.listFile(item["_id"]):
                file_path = os.path.join(tmp_dir, file["name"])
                logger.debug(f"Downloading {file_path}")
                girder_client.downloadFile(
                    file["_id"],
                    file_path
                )
                logger.debug(f"Downloaded {file_path}")
                file_list.append(file_path)

            if len(file_list) > 1:
                raise Exception(
                    "You are trying to load more than one file. \
                    If so, please load a compressed archive."
                )

            image_data = load_file(file_list[0])

        for view in self.views:
            view.add_volume(image_data)

        ctrl.view_update()

    def set_obliques_visibility(self, visible):
        state.display_obliques = True
        for view in self.twod_views:
            view.set_obliques_visibility(visible)
        ctrl.view_update()

    def _build_ui(self):
        with self:
            with VRow(style="height:50%", no_gutters=True):
                with VCol(cols=6):
                    with SliceView(0) as sag_view:
                        self.twod_views.append(sag_view)
                        self.views.append(sag_view)
                with VCol(cols=6):
                    with ThreeDView() as threed_view:
                        self.threed_views.append(threed_view)
                        self.views.append(threed_view)

            with VRow(style="height:50%", no_gutters=True):
                with VCol(cols=6):
                    with SliceView(1) as cor_view:
                        self.twod_views.append(cor_view)
                        self.views.append(cor_view)
                with VCol(cols=6):
                    with SliceView(2) as ax_view:
                        self.twod_views.append(ax_view)
                        self.views.append(ax_view)

