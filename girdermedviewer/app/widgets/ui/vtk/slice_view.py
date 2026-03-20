import logging
from enum import Enum

from undo_stack import Signal

from girdermedviewer.app.widgets.utils.scene_utils import VolumeLayer

from ...utils import (
    debounce,
    get_number_of_slices,
    get_position_from_slice_index,
    get_reslice_center,
    get_reslice_normals,
    get_reslice_window_level,
    get_slice_index_from_position,
    render_mesh_in_slice,
    render_volume_as_overlay_in_slice,
    render_volume_in_slice,
    reset_reslice,
    set_oblique_visibility,
    set_reslice_center,
    set_reslice_normal,
    set_reslice_opacity,
    set_reslice_visibility,
    set_reslice_window_level,
    set_slice_opacity,
    set_slice_visibility,
    set_slice_window_level,
)
from .base_view import ViewType, VtkView

logger = logging.getLogger(__name__)


class SliceOrientation(Enum):
    SAGITTAL = 0
    CORONAL = 1
    AXIAL = 2


class SliceView(VtkView):
    """Display volume as a 2D slice along a given axis/orientation"""

    _debounced_flush_initialized = False
    DEBOUNCED_FLUSH = False
    window_level_changed = Signal(str)

    def __init__(self, orientation: SliceOrientation, ref, **kwargs):
        super().__init__(ref=ref, view_type=ViewType.SLICE, **kwargs)
        self.orientation = orientation
        if SliceView.DEBOUNCED_FLUSH and SliceView._debounced_flush_initialized is False:  # can't use hasattr here
            SliceView._debounced_flush_initialized = True
            self.server.controller.debounced_flush = debounce(0.3)(self.state.flush)

        self.typed_state.bind_changes(
            {
                (self.typed_state.name.position, self.typed_state.name.normals): self.on_cursor_changed,
                self.typed_state.name.are_obliques_visible: self.on_obliques_visibility_changed,
            }
        )

        # in addition to self.ctrl.view_update for any view:
        self.ctrl.slice_view_update.add(self.update)
        # If a view is in animation, the other views must also be in animation to
        # be rendered
        self.ctrl.start_animation.add(self.start_animation)
        self.ctrl.stop_animation.add(self.stop_animation)

        self._build_ui()

    def unregister_data(self, data_id, only_data=None):
        # Do no remove ResliceImageViewer if there is still primary volumes
        remove_prop = not (self.is_primary_volume(data_id) and self.has_multiple_primary_volumes())
        super().unregister_data(data_id, only_data, remove_prop)

        if not self.has_primary_volume():
            self.typed_state.data.normals = None
            self.typed_state.data.are_obliques_visible = False
            if not self.has_secondary_volume():
                self.typed_state.data.position = None

    def flush(self):
        if SliceView.DEBOUNCED_FLUSH:
            self.ctrl.debounced_flush()
        else:
            self.state.flush()

    def get_reslice_image_viewer(self, data_id=None):
        """
        Return the primary volume image viewer if any.
        :param data_id if provided returns only if it matches data_id.
        """
        ids = [data_id] if data_id in self.data else self.data.keys()
        data = [self.get_data(id) for id in ids if self.is_primary_volume(id)]
        return data[0] if len(data) > 0 else None

    def get_image_slices(self, data_id=None):
        ids = [data_id] if data_id in self.data else self.data.keys()
        return [self.get_data(id) for id in ids if self.is_secondary_volume(id)]

    def get_mesh_slices(self, data_id=None):
        data = [self.data[data_id]] if data_id in self.data else self.data.values()
        return [obj for objs in data for obj in objs if obj.IsA("vtkActor")]

    def _add_primary_volume(self, data_id, image_data):
        reslice_image_viewer = render_volume_in_slice(
            image_data, self.renderer, self.orientation.value, obliques=self.typed_state.data.are_obliques_visible
        )
        self.register_data(data_id, reslice_image_viewer)

        reslice_cursor_widget = reslice_image_viewer.GetResliceCursorWidget()
        reslice_image_viewer.AddObserver("InteractionEvent", self.on_slice_scroll)
        reslice_cursor_widget.AddObserver("InteractionEvent", self.on_reslice_cursor_interaction)
        reslice_cursor_widget.AddObserver("EndInteractionEvent", self.on_reslice_cursor_end_interaction)
        reslice_image_viewer.GetInteractorStyle().AddObserver("WindowLevelEvent", self.on_window_leveling)

        self.typed_state.data.are_obliques_visible = True

        self.update()

        self.on_reslice_cursor_interaction(self.get_reslice_image_viewer(), None)

    def _add_secondary_volume(self, data_id, image_data):
        actor = render_volume_as_overlay_in_slice(image_data, self.renderer, self.orientation.value)
        self.register_data(data_id, actor)
        self.update()

    def add_volume(self, data_id, image_data, layer: VolumeLayer):
        if layer == VolumeLayer.PRIMARY:
            self._add_primary_volume(data_id, image_data)
            self.on_reslice_cursor_interaction(self.get_reslice_image_viewer(), None)
        elif layer == VolumeLayer.SECONDARY:
            self._add_secondary_volume(data_id, image_data)

    def add_mesh(self, data_id, poly_data):
        actor = render_mesh_in_slice(poly_data, self.orientation.value, self.renderer)
        self.register_data(data_id, actor)
        self.update()

    def is_primary_volume(self, data_id):
        """
        :see-also has_primary_volume, is_secondary_volume, get_reslice_image_viewer
        """
        data = self.get_data(data_id)
        if not data:
            return False
        if data.IsA("vtkResliceImageViewer"):
            return True
        if data.IsA("vtkImageSlice"):
            return False
        return None

    def is_secondary_volume(self, data_id):
        """
        :see-also is_primary_volume, get_image_slices
        """
        data = self.get_data(data_id)
        if not data:
            return False
        if data.IsA("vtkImageSlice"):
            return True
        if data.IsA("vtkResliceImageViewer"):
            return False
        return None

    def has_primary_volume(self):
        return self.get_reslice_image_viewer() is not None

    def has_multiple_primary_volumes(self):
        return len([data_id for data_id in self.data if self.is_primary_volume(data_id)]) > 1

    def has_secondary_volume(self):
        return len(self.get_image_slices()) > 0

    def reset(self):
        reslice_image_viewer = self.get_reslice_image_viewer()
        if reslice_image_viewer is not None:
            reset_reslice(reslice_image_viewer)
            self.update()

    def on_obliques_visibility_changed(self, obliques_visibility, **_kwargs):
        reslice_image_viewer = self.get_reslice_image_viewer()
        if reslice_image_viewer is not None:
            set_oblique_visibility(reslice_image_viewer, obliques_visibility)
            self.update()

    def set_volume_visibility(self, data_id: str, visible: bool) -> None:
        logger.debug(f"set_volume_visibility({data_id}): {visible}")
        modified = False
        reslice_image_viewer = self.get_reslice_image_viewer(data_id)
        if reslice_image_viewer is not None:
            modified = set_reslice_visibility(reslice_image_viewer, visible)
        for slice in self.get_image_slices(data_id):
            modified = set_slice_visibility(slice, visible) or modified
        if modified:
            self.update()

    def set_volume_opacity(self, data_id, opacity):
        logger.debug(f"set_volume_opacity({data_id}): {opacity}")
        modified = False
        reslice_image_viewer = self.get_reslice_image_viewer(data_id)
        if reslice_image_viewer is not None:
            modified = set_reslice_opacity(reslice_image_viewer, opacity)
        for slice in self.get_image_slices(data_id):
            modified = set_slice_opacity(slice, opacity) or modified
        if modified:
            self.update()

    def set_volume_window_level(self, data_id, window_level):
        logger.debug(f"set_volume_window_level({data_id}): {window_level}")
        modified = False
        reslice_image_viewer = self.get_reslice_image_viewer(data_id)
        if reslice_image_viewer is not None:
            modified = set_reslice_window_level(reslice_image_viewer, window_level)
        for slice in self.get_image_slices(data_id):
            modified = set_slice_window_level(slice, window_level) or modified
        if modified:
            self.update()

    def set_volume_window_level_min_max(self, data_id, window_level_min_max):
        """
        :see-also set_volume_window_level
        """
        if window_level_min_max is not None:
            window = window_level_min_max[1] - window_level_min_max[0]
            level = (window_level_min_max[0] + window_level_min_max[1]) / 2
            self.set_volume_window_level(data_id, (window, level))

    def on_window_leveling(self, *_args):
        window_level_value = get_reslice_window_level(self.get_reslice_image_viewer())
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
        if self.typed_state.data.position != new_position:
            self.typed_state.data.position = new_position
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
        self.typed_state.data.position = get_reslice_center(reslice_image_widget)
        self.typed_state.data.normals = get_reslice_normals(reslice_image_widget)
        # Flushing will trigger rendering
        self.flush()

    def on_reslice_cursor_end_interaction(self, _reslice_image_widget, _event):
        self.state.flush()  # flush state.position

    def on_cursor_changed(self, position, normals, **_kwargs):
        if position is not None and normals is not None:
            set_reslice_center(self.get_reslice_image_viewer(), position)
            set_reslice_normal(self.get_reslice_image_viewer(), normals[self.orientation.value], self.orientation.value)
            self.update()

    def get_slice_range(self):
        reslice_image_viewer = self.get_reslice_image_viewer()
        return [0, get_number_of_slices(reslice_image_viewer, self.orientation.value)]

    def get_slice(self):
        reslice_image_viewer = self.get_reslice_image_viewer()
        return get_slice_index_from_position(
            self.typed_state.data.position, reslice_image_viewer, self.orientation.value
        )

    def set_slice(self, slice):
        reslice_image_viewer = self.get_reslice_image_viewer()
        position = get_position_from_slice_index(slice, reslice_image_viewer, self.orientation.value)
        if position is not None and self.typed_state.data.position != position:
            self.typed_state.data.position = position
            self.flush()

    def on_window_level_changed(self, window_level, **_kwargs):
        logger.debug(f"set_window_level: {window_level}")
        modified = set_reslice_window_level(self.get_reslice_image_viewer(), window_level)
        if modified:
            self.update()
