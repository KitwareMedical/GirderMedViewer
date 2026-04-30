import logging

from trame_server import Server
from vtk import vtkBoxRepresentation, vtkBoxWidget2, vtkPolyData
from vtkmodules.vtkRenderingCore import vtkActor

from ....ui import PlaceROIState, PlaceROIUI, PointState
from ....utils import render_mesh_in_slice, set_mesh_visibility
from ..views_logic import ViewsLogic
from .base_tool_logic import BaseToolLogic

logger = logging.getLogger(__name__)


class PlaceROILogic(BaseToolLogic[PlaceROIState]):
    def __init__(self, server: Server, views_logic: ViewsLogic) -> None:
        super().__init__(server, views_logic, PlaceROIState)
        self._min_bounds_state = self._typed_state.get_sub_state(self.name.min_roi_bounds)
        self._max_bounds_state = self._typed_state.get_sub_state(self.name.max_roi_bounds)

        self.box = vtkBoxRepresentation()
        self.poly_data = vtkPolyData()
        self.box_widget = vtkBoxWidget2()
        self.box_actors: list[vtkActor] = []

        self.box_widget.SetRepresentation(self.box)
        self.box_widget.RotationEnabledOff()
        self.box.SetPlaceFactor(1.0)

        self._update_slice_rep()

        self.box_widget.AddObserver("InteractionEvent", self._update_from_widget)
        self.bind_changes(
            {
                self.name.is_roi_locked: self._on_lock_toggled,
                (self.name.min_roi_bounds, self.name.max_roi_bounds): self._update,
            }
        )

        self._add_roi_to_views()

    def _add_roi_to_views(self):
        for view_logic in self._views_logic.threed_views:
            self.box_widget.SetInteractor(view_logic.renderer.GetRenderWindow().GetInteractor())
            self.box_widget.SetCurrentRenderer(view_logic.renderer)

        for view_logic in self._views_logic.slice_views:
            actor = render_mesh_in_slice(self.poly_data, view_logic.orientation.value, view_logic.renderer)
            self.box_actors.append(actor)

        self.set_enabled(False)

    def _get_bounds(self):
        return (
            self.data.min_roi_bounds.pos_x,
            self.data.max_roi_bounds.pos_x,
            self.data.min_roi_bounds.pos_y,
            self.data.max_roi_bounds.pos_y,
            self.data.min_roi_bounds.pos_z,
            self.data.max_roi_bounds.pos_z,
        )

    def _set_bounds(self, bounds: tuple[float]) -> None:
        if self.data.is_roi_locked:
            return
        self._min_bounds_state.set_dataclass(PointState(round(bounds[0], 2), round(bounds[2], 2), round(bounds[4], 2)))
        self._max_bounds_state.set_dataclass(PointState(round(bounds[1], 2), round(bounds[3], 2), round(bounds[5], 2)))

    def _on_lock_toggled(self, locked: bool) -> None:
        if locked:
            self.box_widget.ProcessEventsOff()
        else:
            self.box_widget.ProcessEventsOn()

    def _update_slice_rep(self) -> None:
        self.box.GetPolyData(self.poly_data)

    def _update_from_widget(self, *_args) -> None:
        if self.data.is_roi_locked:
            return
        new_bounds = self.box.GetBounds()
        self._set_bounds(new_bounds)
        self.state.flush()

    def _update(self, min_roi_bounds: PointState, max_roi_bounds: PointState) -> None:
        if self.data.is_roi_locked or min_roi_bounds.pos_x is None or max_roi_bounds.pos_x is None:
            return

        roi_bounds = self._get_bounds()
        if roi_bounds != self.box.GetBounds():
            self.box.PlaceWidget(roi_bounds)
        self._update_slice_rep()
        self._views_logic.update_views()

    def _reset(self) -> None:
        self._set_bounds(self.default_bounds)

    def set_default_bounds(self, bounds: tuple[float]) -> None:
        one_sixth_size = (
            (bounds[1] - bounds[0]) / 6,
            (bounds[3] - bounds[2]) / 6,
            (bounds[5] - bounds[4]) / 6,
        )
        center = (
            (bounds[0] + bounds[1]) / 2,
            (bounds[2] + bounds[3]) / 2,
            (bounds[4] + bounds[5]) / 2,
        )
        self.default_bounds = (
            center[0] - one_sixth_size[0],
            center[0] + one_sixth_size[0],
            center[1] - one_sixth_size[1],
            center[1] + one_sixth_size[1],
            center[2] - one_sixth_size[2],
            center[2] + one_sixth_size[2],
        )
        self.name.is_roi_locked = False
        self._reset()

    def set_enabled(self, enabled: bool) -> None:
        for actor in self.box_actors:
            set_mesh_visibility(actor, enabled)
        if enabled:
            self.box_widget.On()
        else:
            self.box_widget.Off()

    def set_ui(self, ui: PlaceROIUI) -> None:
        ui.reset_clicked.connect(self._reset)
