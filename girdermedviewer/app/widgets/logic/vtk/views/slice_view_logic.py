import logging
from enum import Enum

from ....ui import ViewUI
from ....utils import (
    ViewType,
    VolumeLayer,
    debounce,
    get_number_of_slices,
    get_position_from_slice_index,
    get_reslice_center,
    get_reslice_normals,
    get_reslice_window_level,
    get_slice_index_from_position,
    reset_reslice,
    set_oblique_visibility,
    set_reslice_center,
    set_reslice_normal,
    set_reslice_window_level,
)
from ..handlers.volume_handler import VolumeTwoDHandler
from .view_logic import ViewLogic

logger = logging.getLogger(__name__)


class SliceOrientation(Enum):
    SAGITTAL = 0
    CORONAL = 1
    AXIAL = 2


def get_orientation_from_view_type(view_type: ViewType) -> SliceOrientation | None:
    return SliceOrientation.__members__.get(view_type.name)


class SliceViewLogic(ViewLogic):
    """Display volume as a 2D slice along a given axis/orientation"""

    _debounced_flush_initialized = False
    DEBOUNCED_FLUSH = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.orientation = get_orientation_from_view_type(self.type)

        if (
            SliceViewLogic.DEBOUNCED_FLUSH and SliceViewLogic._debounced_flush_initialized is False
        ):  # can't use hasattr here
            SliceViewLogic._debounced_flush_initialized = True
            self.server.controller.debounced_flush = debounce(0.3)(self.state.flush)

        self._views_state.bind_changes(
            {
                (self._views_state.name.position, self._views_state.name.normals): self._on_position_or_normals_changed,
                self._views_state.name.are_obliques_visible: self.on_obliques_visibility_changed,
            }
        )

        self.volume_handler = VolumeTwoDHandler(self.color_preset_parser)

    def set_ui(self, ui: ViewUI):
        super().set_ui(ui)
        ui.slider_ui.slice_updated.connect(self.set_slice)

    def reset(self):
        reslice_image_viewer = self.volume_handler.get_reslice_image_viewer()
        if reslice_image_viewer is not None:
            reset_reslice(reslice_image_viewer)
            self.update()

    def add_volume(self, data_id, image_data, layer: VolumeLayer):
        if layer == VolumeLayer.PRIMARY:
            self._views_state.data.are_obliques_visible = True
            self.volume_handler.add_primary_volume(
                data_id, image_data, self.orientation, self._views_state.data.are_obliques_visible
            )
            self._set_reslice_interaction()
            self.update()
        elif layer == VolumeLayer.SECONDARY:
            self.volume_handler.add_secondary_volume(data_id, image_data, self.orientation)
            self.update()

    def add_mesh(self, data_id, poly_data):
        self.mesh_handler.add_mesh_in_slice(data_id, poly_data, self.orientation)
        self.update()

    def remove_volume(self, data_id, only_data=None):
        super().remove_volume(data_id, only_data)

        if not self.volume_handler.has_primary_volume():
            self._views_state.data.normals = None
            self._views_state.data.are_obliques_visible = False
            if not self.volume_handler.has_secondary_volume():
                self._views_state.data.position = None

    def flush(self):
        if SliceViewLogic.DEBOUNCED_FLUSH:
            self.ctrl.debounced_flush()
        else:
            self.state.flush()

    def _set_reslice_interaction(self):
        reslice_image_viewer = self.volume_handler.get_reslice_image_viewer()
        reslice_cursor_widget = reslice_image_viewer.GetResliceCursorWidget()
        reslice_image_viewer.AddObserver("InteractionEvent", self.on_slice_scroll)
        reslice_cursor_widget.AddObserver("InteractionEvent", self.on_reslice_cursor_interaction)
        reslice_cursor_widget.AddObserver("EndInteractionEvent", self.on_reslice_cursor_end_interaction)
        reslice_image_viewer.GetInteractorStyle().AddObserver("WindowLevelEvent", self.on_window_leveling)
        self.on_reslice_cursor_interaction(reslice_image_viewer, None)

    def on_obliques_visibility_changed(self, obliques_visibility, **_kwargs):
        reslice_image_viewer = self.volume_handler.get_reslice_image_viewer()
        if reslice_image_viewer is not None:
            set_oblique_visibility(reslice_image_viewer, obliques_visibility)
            self.update()

    def on_window_leveling(self, *_args):
        window_level_value = get_reslice_window_level(self.volume_handler.get_reslice_image_viewer())
        self.window_level_changed(window_level_value)

    def on_slice_scroll(self, reslice_image_viewer, _event):
        """
        Triggered when scrolling the current image.
        There are 2 possible user interactions to modify the cursor:
         - scroll
         - cursor interaction

        :see-also on_reslice_cursor_interaction
        """
        new_position = get_reslice_center(reslice_image_viewer)
        if self._views_state.data.position != new_position:
            self._views_state.data.position = new_position
        # Because it is called within a co-routine, position is not
        # flushed right away.
        self.flush()

    def on_reslice_cursor_interaction(self, reslice_image_widget, _event):
        """
        Triggered when interacting with oblique lines.
        Because it is called within a co-routine, position is not flushed right away.

        There are 2 possible user interactions to modify the cursor:
         - scroll
         - cursor interaction
        :see-also on_slice_scroll
        """
        self._views_state.data.position = get_reslice_center(reslice_image_widget)
        self._views_state.data.normals = get_reslice_normals(reslice_image_widget)
        # Flushing will trigger rendering
        self.flush()

    def on_reslice_cursor_end_interaction(self, _reslice_image_widget, _event):
        self.state.flush()  # flush state.position

    @debounce(0.3)
    def _update_slider(self, *_args):
        range = self.get_slice_range()
        self.data.slider_state.min_value = range[0]
        self.data.slider_state.max_value = range[1]
        self.data.slider_state.value = self.get_slice()
        self.flush()

    def _update_position_and_normals_in_view(self, position, normals):
        set_reslice_center(self.volume_handler.get_reslice_image_viewer(), position)
        set_reslice_normal(
            self.volume_handler.get_reslice_image_viewer(), normals[self.orientation.value], self.orientation.value
        )
        self.flush()

    def _on_position_or_normals_changed(self, position, normals):
        if position is not None and normals is not None:
            self._update_position_and_normals_in_view(position, normals)
            self._update_slider()

            self.update()

    def get_slice_range(self):
        reslice_image_viewer = self.volume_handler.get_reslice_image_viewer()
        return [0, get_number_of_slices(reslice_image_viewer, self.orientation.value)]

    def get_slice(self):
        reslice_image_viewer = self.volume_handler.get_reslice_image_viewer()
        return get_slice_index_from_position(
            self._views_state.data.position, reslice_image_viewer, self.orientation.value
        )

    def set_slice(self, slice):
        reslice_image_viewer = self.volume_handler.get_reslice_image_viewer()
        position = get_position_from_slice_index(slice, reslice_image_viewer, self.orientation.value)
        if position is not None and self._views_state.data.position != position:
            self._views_state.data.position = position
            self.flush()

    def on_window_level_changed(self, window_level, **_kwargs):
        logger.debug(f"set_window_level: {window_level}")
        modified = set_reslice_window_level(self.volume_handler.get_reslice_image_viewer(), window_level)
        if modified:
            self.update()
