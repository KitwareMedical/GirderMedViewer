import logging
from abc import abstractmethod
from typing import Any, Generic, TypeVar

from trame_server.core import Server
from trame_server.utils.typed_state import TypedState
from undo_stack import Signal
from vtk import vtkImageData

from ....ui import ViewsState, ViewState, ViewType, ViewUI
from ....utils import (
    ColorPresetParser,
    SceneObjectSubtype,
    VolumeLayer,
    VolumePresetParser,
)
from ...base_logic import BaseLogic
from ...scene.objects.volume_object_logic import VolumeDisplay
from ..handlers.mesh_handler import MeshHandler
from ..handlers.volume_handler import VolumeHandler
from ..place_roi_logic import PlaceROILogic

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=VolumeHandler)


class ViewLogic(BaseLogic[ViewState], Generic[T]):
    window_level_changed = Signal(str)
    volume_handler: T

    def __init__(
        self,
        server: Server,
        view_type: ViewType,
        volume_preset_parser: VolumePresetParser,
        color_preset_parser: ColorPresetParser,
    ) -> None:
        super().__init__(server, ViewState, view_type.value)
        self.type = view_type
        self.volume_preset_parser = volume_preset_parser
        self.color_preset_parser = color_preset_parser

        self.mesh_handler = MeshHandler(color_preset_parser)

        self._views_state = TypedState(self.state, ViewsState)

    def set_ui(self, ui: ViewUI) -> None:
        self.renderer = ui.renderer
        self.mesh_handler.set_renderer(ui.renderer)
        self.volume_handler.set_renderer(ui.renderer)
        self.update = ui.update

    @abstractmethod
    def reset(self) -> None:
        pass

    @abstractmethod
    def add_volume(
        self,
        data_id: str,
        data: vtkImageData,
        display_properties: VolumeDisplay,
        layer: VolumeLayer,
        subtype: SceneObjectSubtype,
    ) -> None:
        pass

    @abstractmethod
    def add_mesh(self, data_id: str, data: vtkImageData) -> None:
        pass

    @abstractmethod
    def init_roi(self, roi: PlaceROILogic) -> None:
        pass

    def remove_volume(self, data_id: str, only_data: Any | None = None) -> None:
        self.volume_handler.unregister_data(data_id, only_data)

    def remove_mesh(self, data_id: str, only_data: Any | None = None) -> None:
        self.mesh_handler.unregister_data(data_id, only_data)
