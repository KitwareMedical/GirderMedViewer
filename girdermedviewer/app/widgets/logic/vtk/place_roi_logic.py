import logging

from trame_server import Server
from undo_stack import Signal
from vtk import vtkBoxRepresentation, vtkBoxWidget2, vtkPolyData

from ...ui import PlaceROIState, PlaceROIUI
from ..base_logic import BaseLogic

logger = logging.getLogger(__name__)


class PlaceROILogic(BaseLogic[PlaceROIState]):
    roi_updated = Signal()

    def __init__(self, server: Server) -> None:
        super().__init__(server, PlaceROIState)
        self._id = "ROI"
        self.box_widget = vtkBoxWidget2()

        self.slice_rep = vtkPolyData()
        self.threed_rep = vtkBoxRepresentation()

        self.box_widget.SetRepresentation(self.threed_rep)
        self.box_widget.RotationEnabledOff()
        self.threed_rep.SetPlaceFactor(1.0)

        self._update_slice_rep()

        self.box_widget.AddObserver("InteractionEvent", self._update_from_widget)
        self.bind_changes(
            {
                self.name.is_roi_locked: self._on_lock_toggled,
                self.name.roi_bounds: self._update,
            }
        )

    def _set_bounds(self, bounds: tuple[float], clean: bool = False) -> None:
        if self.data.is_roi_locked:
            return
        self.data.roi_bounds = bounds
        if clean:
            self.state.clean(self.name.roi_bounds)

    def _on_lock_toggled(self, locked: bool) -> None:
        if locked:
            self.box_widget.ProcessEventsOff()
        else:
            self.box_widget.ProcessEventsOn()

    def _update_slice_rep(self) -> None:
        self.threed_rep.GetPolyData(self.slice_rep)

    def _update_from_widget(self, *_args) -> None:
        if self.data.is_roi_locked:
            return
        new_bounds = self.threed_rep.GetBounds()
        self._set_bounds(new_bounds, clean=True)
        self._update_slice_rep()
        self.roi_updated()

    def _update(self, roi_bounds: tuple[float]) -> None:
        if self.data.is_roi_locked:
            return
        self.threed_rep.PlaceWidget(roi_bounds)
        self._update_slice_rep()
        self.roi_updated()

    def _reset(self) -> None:
        self._set_bounds(self.default_bounds)

    def set_default_bounds(self, bounds: tuple[float]) -> None:
        one_sixth_size = (
            (bounds[1] - bounds[0]) / 6,
            (bounds[3] - bounds[2]) / 6,
            (bounds[5] - bounds[4]) / 6,
        )
        center = (
            bounds[0] / 2 + bounds[1] / 2,
            bounds[1] / 2 + bounds[2] / 2,
            bounds[3] / 2 + bounds[4] / 2,
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

    def enable_widget(self, enable: bool) -> None:
        if enable:
            self.box_widget.On()
        else:
            self.box_widget.Off()

    def set_ui(self, ui: PlaceROIUI) -> None:
        ui.reset_clicked.connect(self._reset)
