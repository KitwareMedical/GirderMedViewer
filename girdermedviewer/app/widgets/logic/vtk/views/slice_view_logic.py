import logging
from enum import Enum

from vtk import vtkImageData, vtkPolyData
from vtkmodules.vtkInteractionImage import vtkResliceImageViewer
from vtkmodules.vtkInteractionWidgets import vtkResliceCursorWidget

from ....ui import PointState, ViewType, ViewUI
from ....utils import (
    SceneObjectSubtype,
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
from ...scene.objects.mesh_object_logic import MeshDisplay
from ...scene.objects.volume_object_logic import VolumeDisplay
from ..handlers.volume_handler import VolumeSliceHandler
from .view_logic import ViewLogic

logger = logging.getLogger(__name__)


class SliceOrientation(Enum):
    SAGITTAL = 0
    CORONAL = 1
    AXIAL = 2


def get_orientation_from_view_type(view_type: ViewType) -> SliceOrientation | None:
    return SliceOrientation.__members__.get(view_type.name)


class SliceViewLogic(ViewLogic[VolumeSliceHandler]):
    """Display volume as a 2D slice along a given axis/orientation"""

    _debounced_flush_initialized = False
    DEBOUNCED_FLUSH = False

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.orientation = get_orientation_from_view_type(self.type)

        if (
            SliceViewLogic.DEBOUNCED_FLUSH and SliceViewLogic._debounced_flush_initialized is False
        ):  # can't use hasattr here
            SliceViewLogic._debounced_flush_initialized = True
            self.ctrl.debounced_flush = debounce(0.3)(self.state.flush)

        # self.bind_changes({self.name.slider_state.value: self._set_slice})
        self._views_state.bind_changes(
            {
                # (self._views_state.name.position, self._views_state.name.normals): self._on_position_or_normals_changed,
                self._views_state.name.are_obliques_visible: self.on_obliques_visibility_changed,
            }
        )

        self.volume_handler = VolumeSliceHandler(self.color_preset_parser, self.orientation.value)

    @property
    def position(self) -> tuple[float]:
        return (
            self._views_state.data.position.pos_x,
            self._views_state.data.position.pos_y,
            self._views_state.data.position.pos_z,
        )

    @position.setter
    def position(self, position_tuple: tuple[float]) -> None:
        if len(position_tuple) == 3:
            (
                self._views_state.data.position.pos_x,
                self._views_state.data.position.pos_y,
                self._views_state.data.position.pos_z,
            ) = tuple(round(pos, 3) for pos in position_tuple)

    def set_ui(self, ui: ViewUI) -> None:
        super().set_ui(ui)
        ui.slider_ui.slice_updated.connect(self._set_slice)

    def reset(self) -> None:
        reslice_image_viewer = self.volume_handler.get_reslice_image_viewer()
        if reslice_image_viewer is not None:
            reset_reslice(reslice_image_viewer)
            self.update()

    def add_volume(
        self,
        data_id: str,
        image_data: vtkImageData,
        display_properties: VolumeDisplay,
        layer: VolumeLayer,
        subtype: SceneObjectSubtype,
    ):
        is_primary = False
        if subtype == SceneObjectSubtype.LABELMAP and layer == VolumeLayer.SECONDARY:
            self.volume_handler.add_labelmap(data_id, image_data)
        elif layer == VolumeLayer.PRIMARY:
            is_primary = True
            self.volume_handler.add_primary_volume(data_id, image_data)
            self._set_reslice_interaction()
        elif layer == VolumeLayer.SECONDARY:
            self.volume_handler.add_secondary_volume(data_id, image_data)
        else:
            raise ValueError("Volume layer cannot be undefined.")

        self.volume_handler.apply_volume_display_properties(data_id, display_properties, is_primary)

    def add_mesh(self, data_id: str, poly_data: vtkPolyData, display_properties: MeshDisplay) -> None:
        self.mesh_handler.add_mesh_in_slice(data_id, poly_data, self.orientation.value)
        self.mesh_handler.apply_mesh_display_properties(data_id, display_properties)

    def flush(self) -> None:
        if SliceViewLogic.DEBOUNCED_FLUSH:
            self.ctrl.debounced_flush()
        else:
            self.state.flush()

    def _set_reslice_interaction(self) -> None:
        reslice_image_viewer = self.volume_handler.get_reslice_image_viewer()
        reslice_cursor_widget = reslice_image_viewer.GetResliceCursorWidget()
        reslice_image_viewer.AddObserver("InteractionEvent", self.on_slice_scroll)
        reslice_cursor_widget.AddObserver("InteractionEvent", self.on_reslice_cursor_interaction)
        reslice_cursor_widget.AddObserver("EndInteractionEvent", self.on_reslice_cursor_end_interaction)
        reslice_image_viewer.GetInteractorStyle().AddObserver("WindowLevelEvent", self.on_window_leveling)
        self.on_reslice_cursor_interaction(reslice_image_viewer, None)

    def on_obliques_visibility_changed(self, obliques_visibility: bool, **_kwargs) -> None:
        reslice_image_viewer = self.volume_handler.get_reslice_image_viewer()
        if reslice_image_viewer is not None:
            set_oblique_visibility(reslice_image_viewer, obliques_visibility)
            self.update()

    def on_window_leveling(self, *_args) -> None:
        window_level_value = get_reslice_window_level(self.volume_handler.get_reslice_image_viewer())
        self.window_level_changed(window_level_value)

    def on_slice_scroll(self, reslice_image_viewer: vtkResliceImageViewer, _event) -> None:
        """
        Triggered when scrolling the current image.
        There are 2 possible user interactions to modify the cursor:
         - scroll
         - cursor interaction

        :see-also on_reslice_cursor_interaction
        """
        new_position = get_reslice_center(reslice_image_viewer)
        if self.position != new_position:
            self.position = new_position
        # Because it is called within a co-routine, position is not
        # flushed right away.
        self.flush()

    def on_reslice_cursor_interaction(self, reslice_cursor_widget: vtkResliceCursorWidget, *_args) -> None:
        """
        Triggered when interacting with oblique lines.
        Because it is called within a co-routine, position is not flushed right away.

        There are 2 possible user interactions to modify the cursor:
         - scroll
         - cursor interaction
        :see-also on_slice_scroll
        """
        self.position = get_reslice_center(reslice_cursor_widget)
        self._views_state.data.normals = get_reslice_normals(reslice_cursor_widget)
        # Flushing will trigger rendering
        self.flush()

    def on_reslice_cursor_end_interaction(self, *_args) -> None:
        self.flush()  # flush state.position

    def _update_slider(self, *_args) -> None:
        range = self._get_slice_range()
        self.data.slider_state.min_value = range[0]
        self.data.slider_state.max_value = range[1]
        self.data.slider_state.value = self._get_slice()
        self.flush()

    def _update_position_and_normals_in_view(self, position: PointState, normals: tuple[tuple[float]]) -> None:
        set_reslice_center(
            self.volume_handler.get_reslice_image_viewer(), (position.pos_x, position.pos_y, position.pos_z)
        )
        set_reslice_normal(
            self.volume_handler.get_reslice_image_viewer(), normals[self.orientation.value], self.orientation.value
        )
        self.flush()

    def _on_position_or_normals_changed(self, position: PointState, normals: tuple[tuple[float]] | None) -> None:
        if position.pos_x is not None and normals is not None:
            self._update_position_and_normals_in_view(position, normals)
            self._update_slider()

            self.update()

    def _get_slice_range(self) -> None:
        reslice_image_viewer = self.volume_handler.get_reslice_image_viewer()
        return [0, get_number_of_slices(reslice_image_viewer, self.orientation.value)]

    def _get_slice(self) -> None:
        reslice_image_viewer = self.volume_handler.get_reslice_image_viewer()
        return get_slice_index_from_position(self.position, reslice_image_viewer, self.orientation.value)

    @debounce(0.05)
    def _set_slice(self, slice: int) -> None:
        reslice_image_viewer = self.volume_handler.get_reslice_image_viewer()
        new_position = get_position_from_slice_index(slice, reslice_image_viewer, self.orientation.value)
        if new_position is not None and self.position != new_position:
            self.position = new_position/
            self._update_position_and_normals_in_view(new_position, normals)
            self.flush()

    def on_window_level_changed(self, window_level: tuple[float], **_kwargs) -> None:
        logger.debug(f"set_window_level: {window_level}")
        modified = set_reslice_window_level(self.volume_handler.get_reslice_image_viewer(), window_level)
        if modified:
            self.update()
