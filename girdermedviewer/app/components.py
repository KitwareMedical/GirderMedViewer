import asyncio
from math import floor
import logging
import sys
from time import time

from collections import defaultdict
from trame_server.utils.asynchronous import create_task
from trame.app import get_server
from trame.widgets import gwc, html, vtk
from trame.widgets.vuetify2 import (VContainer, VRow, VCol, VTooltip,
                                    Template, VBtn, VIcon, VCheckbox)
from typing import Callable, Optional
from .girder_utils import FileDownloader, CacheMode
from .utils import debounce
from .vtk_utils import (
    create_rendering_pipeline,
    get_reslice_center,
    get_reslice_normals,
    load_file,
    load_mesh,
    render_mesh_in_3D,
    render_mesh_in_slice,
    render_volume_in_3D,
    render_volume_in_slice,
    reset_reslice,
    reset_3D,
    set_oblique_visibility,
    set_reslice_center
)
from girder_client import GirderClient

logging.basicConfig(stream=sys.stdout)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

server = get_server(client_type="vue2")
state, ctrl = server.state, server.controller


@debounce(0.3)
def debounced_flush():
    state.flush()


class GirderDrawer(VContainer):
    def __init__(self, quad_view, **kwargs):
        super().__init__(
            classes="fill-height pa-0",
            **kwargs
        )
        self.quad_view = quad_view
        self._build_ui()

    def _build_ui(self):
        with self:
            with VRow(
                style="height:100%",
                align_content="start",
                justify="center",
                no_gutters=True
            ):
                with VCol(cols=12):
                    GirderFileSelector(self.quad_view)

                with VCol(cols=12):
                    # TODO To Replace with ItemList
                    gwc.GirderDataDetails(
                        v_if=("detailed.length > 0",),
                        action_keys=("action_keys",),
                        value=("detailed",)
                    )
                with VCol(v_if=("displayed.length > 0",), cols="auto"):
                    Button(
                        tooltip="Clear View",
                        icon="mdi-close-box",
                        click=self.clear_views,
                        loading=("file_loading_busy",),
                        size=60,
                        disabled=("file_loading_busy",),
                    )

    def clear_views(self):
        self.quad_view.clear()
        state.displayed = []


class GirderFileSelector(gwc.GirderFileManager):
    def __init__(self, quad_view, **kwargs):
        state.selected_in_location = []
        super().__init__(
            v_if=("user",),
            v_model=("selected_in_location",),
            location=("location",),
            update_location=(self.update_location, "[$event]"),
            rowclick=(
                self.toggle_item,
                "[$event]"
            ),
            **kwargs
        )
        self.quad_view = quad_view
        girder_client = GirderClient(apiUrl=state.api_url)
        cache_mode = CacheMode(state.cache_mode) if state.cache_mode else CacheMode.No
        self.file_downloader = FileDownloader(girder_client, state.temp_dir, cache_mode)
        # FIXME do not use global variable
        global file_selector
        file_selector = self

        state.change("location", "displayed")(self.on_location_changed)
        state.change("api_url")(self.set_api_url)
        state.change("user")(self.set_user)

    def toggle_item(self, item):
        if item.get('_modelType') != 'item':
            return
        # Ignore double click on item
        clicked_time = time()
        if clicked_time - state.last_clicked < 1:
            return
        state.last_clicked = clicked_time
        is_selected = item in state.displayed
        logger.debug(f"Toggle item {item} selected={is_selected}")
        if is_selected:
            self.unselect_item(item)
        else:
            self.select_item(item)

    def update_location(self, new_location):
        """
        Called each time the user browse through the GirderFileManager.
        """
        logger.debug(f"Updating location to {new_location}")
        state.location = new_location

    def unselect_item(self, item):
        state.displayed = [i for i in state.displayed if i != item]
        self.quad_view.remove_data(item["_id"])

    def unselect_items(self):
        while len(state.displayed) > 0:
            self.unselect_item(state.displayed[0])

    def select_item(self, item):
        assert item.get('_modelType') == 'item', "Only item can be selected"
        is_mesh = item.get('name', '').endswith('.stl')
        # only 1 volume at a time for now
        if not is_mesh:
            self.unselect_items()

        state.displayed = state.displayed + [item]

        self.create_load_task(item)

    def create_load_task(self, item):
        logger.debug(f"Creating load task for {item}")
        state.file_loading_busy = True
        state.flush()

        async def load():
            await asyncio.sleep(1)
            try:
                self.load_item(item)
            finally:
                state.file_loading_busy = False
                state.flush()

        create_task(load())

    def load_item(self, item):
        logger.debug(f"Loading files {item}")
        try:
            logger.debug("Listing files")
            files = list(self.file_downloader.get_item_files(item))
            logger.debug(f"Files {files}")
            if len(files) != 1:
                raise Exception(
                    "No file to load. Please check the selected item."
                    if (not files) else
                    "You are trying to load more than one file. \
                    If so, please load a compressed archive."
                )
            with self.file_downloader.download_file(files[0]) as file_path:
                self.quad_view.load_files(file_path, item["_id"])
        except Exception as e:
            logger.error(f"Error loading file {item['_id']}: {e}")
            self.unselect_item(item)

    def set_api_url(self, api_url, **kwargs):
        logger.debug(f"Setting api_url to {api_url}")
        self.file_downloader.girder_client = GirderClient(apiUrl=api_url)

    def set_token(self, token):
        self.file_downloader.girder_client.setToken(token)

    def on_location_changed(self, **kwargs):
        logger.debug(f"Location/Displayed changed to {state.location}/{state.displayed}")
        location_id = state.location.get("_id", "") if state.location else ""
        state.selected_in_location = [item for item in state.displayed
                                      if item["folderId"] == location_id]
        state.detailed = state.selected_in_location if state.selected_in_location else [state.location]

    def set_user(self, user, **kwargs):
        logger.debug(f"Setting user to {user}")
        if user:
            state.location = state.default_location or user
            self.set_token(state.token)
        else:
            self.unselect_items()
            state.location = None
            self.set_token(None)


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
            VCheckbox(
                v_model=("obliques_visibility",),
                off_icon='mdi-eye-outline',
                on_icon='mdi-eye-remove-outline',
                color="black",
                disabled=("displayed.length === 0 || file_loading_busy",)
            )

            Button(
                tooltip="Reset Views",
                icon="mdi-camera-flip-outline",
                click=ctrl.reset,
                disabled=("displayed.length === 0 || file_loading_busy",)
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
        self.data = defaultdict(list)
        ctrl.view_update.add(self.update)

    def register_data(self, data_id, data):
        # Associate data (typically an actor) to data_id so that it can be
        # removed when data_id is unregistered.
        self.data[data_id].append(data)

    def unregister_data(self, data_id, no_render=False):
        for data in self.data[data_id]:
            if data.IsA("vtkVolume"):
                self.renderer.RemoveVolume(data)
            elif data.IsA("vtkActor"):
                self.renderer.RemoveActor(data)
            elif data.IsA("vtkImageViewer2"):
                data.SetupInteractor(None)
                # FIXME: check for leak
                # data.SetRenderer(None)
                # data.SetRenderWindow(None)
        self.data.pop(data_id)
        if not no_render:
            self.update()

    def unregister_all_data(self, no_render=False):
        data_ids = list(self.data.keys())
        for data_id in data_ids:
            self.unregister_data(data_id, True)
        if not no_render:
            self.update()


class SliceView(VtkView):
    """ Display volume as a 2D slice along a given axis """
    def __init__(self, axis, **kwargs):
        super().__init__(**kwargs)
        self.axis = axis
        self._build_ui()

        state.change("position")(self.set_position)

    def add_volume(self, image_data, data_id=None):
        reslice_image_viewer = render_volume_in_slice(
            data_id,
            image_data,
            self.renderer,
            self.axis,
            obliques=state.obliques_visibility
        )
        self.register_data(data_id, reslice_image_viewer)

        reslice_cursor_widget = reslice_image_viewer.GetResliceCursorWidget()
        reslice_image_viewer.AddObserver(
            'InteractionEvent', self.on_slice_scroll)
        reslice_cursor_widget.AddObserver(
            'InteractionEvent', self.on_reslice_axes_interaction)
        reslice_cursor_widget.AddObserver(
            'EndInteractionEvent', self.on_reslice_axes_end_interaction)
        self.update()

    def add_mesh(self, poly_data, data_id=None):
        actor = render_mesh_in_slice(
            data_id,
            poly_data,
            self.renderer
        )
        self.register_data(data_id, actor)
        self.update()

    def reset(self):
        for reslice_image_viewer in self.get_reslice_image_viewers():
            reset_reslice(reslice_image_viewer)
        self.update()

    def set_obliques_visibility(self, visible):
        for reslice_image_viewer in self.get_reslice_image_viewers():
            set_oblique_visibility(reslice_image_viewer, visible)
        self.update()

    def on_slice_scroll(self, reslice_image_viewer, event):
        """
        Triggered when scrolling the current image.
        Because it is called within a co-routine, position is not flushed right away.
        """
        state.position = get_reslice_center(reslice_image_viewer)
        debounced_flush()

    def on_reslice_axes_interaction(self, reslice_image_widget, event):
        """
        Triggered when interacting with oblique lines.
        Because it is called within a co-routine, position is not flushed right away.
        """
        state.position = get_reslice_center(reslice_image_widget)
        state.normals = get_reslice_normals(reslice_image_widget)

    def on_reslice_axes_end_interaction(self, reslice_image_widget, event):
        state.flush()

    def set_position(self, position, **kwargs):
        logger.debug(f"set_position: {position}")
        for reslice_image_viewer in self.get_reslice_image_viewers():
            set_reslice_center(reslice_image_viewer, position)

    def get_reslice_image_viewers(self):
        return [obj for objs in self.data.values() for obj in objs if obj.IsA('vtkResliceImageViewer')]

    def _build_ui(self):
        with self:
            ViewGutter(self)


class ThreeDView(VtkView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._build_ui()

    def add_volume(self, image_data, data_id=None):
        volume = render_volume_in_3D(
            image_data,
            self.renderer
        )
        self.register_data(data_id, volume)
        self.update()

    def add_mesh(self, poly_data, data_id=None):
        actor = render_mesh_in_3D(
            poly_data,
            self.renderer
        )
        self.register_data(data_id, actor)
        self.update()

    def reset(self):
        reset_3D(self.renderer)
        self.update()

    def _build_ui(self):
        with self:
            ViewGutter(self)


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

        ctrl.reset = self.reset
        state.change("obliques_visibility")(self.set_obliques_visibility)

    def remove_data(self, data_id=None):
        for view in self.views:
            view.unregister_data(data_id)
        ctrl.view_update()

    def clear(self):
        for view in self.views:
            view.unregister_all_data()
        ctrl.view_update()

    def set_obliques_visibility(self, obliques_visibility, **kwargs):
        for view in self.twod_views:
            view.set_obliques_visibility(obliques_visibility)
        ctrl.view_update()

    def reset(self):
        for view in self.views:
            view.reset()
        ctrl.view_update()

    def load_files(self, file_path, data_id=None):
        logger.debug(f"Loading file {file_path}")
        if file_path.endswith(".stl"):
            poly_data = load_mesh(file_path)
            for view in self.views:
                view.add_mesh(poly_data, data_id)
        else:
            image_data = load_file(file_path)
            for view in self.views:
                view.add_volume(image_data, data_id)

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
