import logging
import weakref
from abc import abstractmethod
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum

from trame.widgets import html, vtk
from trame.widgets import vuetify3 as v3
from trame_server.utils.typed_state import TypedState
from vtkmodules.vtkCommonDataModel import vtkImageData

from ...utils import (
    Button,
    ColorPresetParser,
    DataArray,
    VolumePresetParser,
    create_rendering_pipeline,
    debounce,
    get_image_data,
    remove_prop,
    set_mesh_opacity,
    set_mesh_solid_color,
    set_mesh_visibility,
)

logger = logging.getLogger(__name__)


class ViewType(Enum):
    SLICE = 0
    THREED = 1


@dataclass
class SliderState:
    value: int | None = None
    min_value: int | None = None
    max_value: int | None = None


@dataclass
class ViewState:
    is_position_menu_visible: bool = False
    position: tuple[float] | None = None
    normals: tuple[tuple[float]] | None = None
    are_obliques_visible: bool = False
    fullscreen: str | None = None


class VtkView(vtk.VtkRemoteView):
    """Base class for VTK views"""

    def __init__(self, ref, view_type: ViewType, **kwargs):
        """ref is also used as id if no id is given. It can be used for CSS styling."""
        renderer, render_window = create_rendering_pipeline()
        super().__init__(
            render_window,
            interactive_quality=80,
            interactive_ratio=1,
            id=kwargs.pop("id", None) or ref,
            ref=ref,  # avoids recreating a view when UI is rebuilt
            **kwargs,
        )
        self.type = view_type
        self.renderer = renderer
        self.data = defaultdict(list)
        self.ctrl.view_update.add(weakref.WeakMethod(self.update))
        self.color_preset_parser: ColorPresetParser | None = None
        self.volume_preset_parser: VolumePresetParser | None = None

        self.typed_state = TypedState(self.state, ViewState)

    def set_volume_preset_parser(self, volume_preset_parser: VolumePresetParser) -> None:
        self.volume_preset_parser = volume_preset_parser

    def set_color_preset_parser(self, color_preset_parser: ColorPresetParser) -> None:
        self.color_preset_parser = color_preset_parser

    def get_data_id(self, data):
        return next((key for key, value in self.data.items() if data in value), None)

    def get_data(self, data_id):
        data = self.data.get(data_id, [])
        return data[0] if len(data) else None

    def get_actors(self, data_id):
        data = [self.data[data_id]] if data_id in self.data else self.data.values()
        return [obj for objs in data for obj in objs if obj.IsA("vtkActor")]

    def get_image_data(self, data_id):
        data = [self.data[data_id]] if data_id in self.data else self.data.values()
        image_data = [get_image_data(obj)
                      for objs in data
                      for obj in objs
                      if get_image_data(obj) is not None]
        return image_data[0] if len(image_data) else None

    def get_glyph_actors(self, data_id):
        data = [self.data[data_id]] if data_id in self.data else self.data.values()
        return [obj for objs in data for obj in objs if obj.IsA("vtkGlyph3DMapper")]

    def register_data(self, data_id, data):
        # Associate data (typically an actor) to data_id so that it can be
        # removed when data_id is unregistered.
        if data in self.data.get(data_id, []):
            return
        self.data[data_id].append(data)

    def unregister_data(self, data_id, only_data=None, remove=True):
        """
        :param only_data removes only the provided data if any, all associated if None
        :param remove removes the prop from the view
        """
        data_list = list(self.data.get(data_id, []))
        for data in data_list:
            if only_data is None or data == only_data:
                if remove:
                    remove_prop(self.renderer, data)
                self.data[data_id].remove(data)
        if len(data_list) == 0:
            self.data.pop(data_id)

        self.update()

    @abstractmethod
    def set_volume_visibility(self, data_id: str, visible: bool, image_data: vtkImageData | None = None) -> None:
        pass

    def set_mesh_visibility(self, data_id: str, visible: bool) -> None:
        modified = False
        for actor in self.get_actors(data_id):
            modified = set_mesh_visibility(actor, visible) or modified
        if modified is not False:
            self.update()

    def set_mesh_opacity(self, data_id, opacity):
        modified = False
        for actor in self.get_actors(data_id):
            modified = set_mesh_opacity(actor, opacity) or modified
        if modified is not False:
            self.update()

    def set_mesh_solid_color(self, data_id, color):
        modified = False
        for actor in self.get_actors(data_id):
            modified = set_mesh_solid_color(actor, color) or modified
        if modified is not False:
            self.update()

    def set_mesh_array_color(
        self, data_id: str, array_obj: DataArray, preset_name: str, is_inverted: bool, preset_range: list[float]
    ):
        if self.color_preset_parser is None:
            return

        logger.debug(f"set_mesh_array_color({data_id}): {preset_name}")
        preset = self.color_preset_parser.get_preset_by_name(preset_name)
        if preset is None:
            return

        modified = False
        for actor in self.get_actors(data_id):
            modified = (
                self.color_preset_parser.apply_preset_to_mesh(actor, array_obj, preset, preset_range, is_inverted)
                or modified
            )
        if modified is not False:
            self.update()

    def _build_ui(self):
        with self:
            ViewGutter(self)


class ViewGutter(html.Div):
    DEBOUNCED_SLIDER_UPDATE = True

    def __init__(self, view: VtkView, **kwargs):
        super().__init__(classes="view-gutter", **kwargs)
        assert view.id is not None
        self.view = view

        self._slider_state = TypedState(self.state, SliderState, namespace=view.ref_name)

        if self.view.type == ViewType.SLICE:
            view.typed_state.bind_changes(
                {
                    (view.typed_state.name.position, view.typed_state.name.normals): debounce(
                        0.3, not ViewGutter.DEBOUNCED_SLIDER_UPDATE
                    )(self._on_slice_view_modified),
                }
            )

        self._build_ui()

    def _on_slice_view_modified(self, *_args):
        range = self.view.get_slice_range()
        self._slider_state.data.min_value = range[0]
        self._slider_state.data.max_value = range[1]
        self._slider_state.data.value = self.view.get_slice()
        self.state.flush()  # FIXME: need to flush manually

    def _build_ui(self):
        with self, html.Div(classes="view-gutter-content"):
            Button(
                click=self.toggle_fullscreen,
                color="white",
                icon=(f"{self.view.typed_state.name.fullscreen} == null ? 'mdi-fullscreen' : 'mdi-fullscreen-exit'",),
                tooltip=(
                    f"{self.view.typed_state.name.fullscreen} == null ? 'Extend to fullscreen' : 'Exit fullscreen'",
                ),
                variant="text",
            )
            if self.view.type == ViewType.SLICE:
                v3.VSlider(
                    v_if=(f"{self._slider_state.name.value} != null",),
                    classes="slice-slider",
                    hide_details=True,
                    direction="vertical",
                    height="100%",
                    v_model=(self._slider_state.name.value, self.view.get_slice()),
                    min=(self._slider_state.name.min_value, self.view.get_slice_range()[0]),
                    max=(self._slider_state.name.max_value, self.view.get_slice_range()[1]),
                    step=1,
                    update_modelValue=(self.view.set_slice, f"[{self._slider_state.name.value}]"),
                    # to lower the framerate when animating the slider
                    start=self.ctrl.start_animation,
                    end=self.ctrl.stop_animation,
                    # needed to prevent None triggers
                )

    def toggle_fullscreen(self):
        self.view.typed_state.data.fullscreen = None if self.view.typed_state.data.fullscreen else self.view.id
