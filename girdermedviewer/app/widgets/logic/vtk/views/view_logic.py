import logging
from abc import abstractmethod

from trame_server.core import Server
from trame_server.utils.typed_state import TypedState
from undo_stack import Signal

from girdermedviewer.app.widgets.logic.vtk.place_roi_logic import PlaceROILogic

from ....ui import ViewsState, ViewState, ViewType, ViewUI
from ....utils import (
    ColorPresetParser,
    VolumePresetParser,
)
from ...base_logic import BaseLogic
from ..handlers.mesh_handler import MeshHandler
from ..handlers.volume_handler import (
    VolumeThreeDHandler,
    VolumeTwoDHandler,
)

logger = logging.getLogger(__name__)


class ViewLogic(BaseLogic[ViewState]):
    window_level_changed = Signal(str)

    def __init__(
        self,
        server: Server,
        view_type: ViewType,
        volume_preset_parser: VolumePresetParser,
        color_preset_parser: ColorPresetParser,
    ):
        super().__init__(server, ViewState, view_type.value)
        self.type = view_type
        self.volume_preset_parser = volume_preset_parser
        self.color_preset_parser = color_preset_parser

        self.mesh_handler = MeshHandler(color_preset_parser)
        self.volume_handler: VolumeTwoDHandler | VolumeThreeDHandler | None = None

        self._views_state = TypedState(self.state, ViewsState)

    def set_ui(self, ui: ViewUI):
        self.renderer = ui.renderer
        self.mesh_handler.set_renderer(ui.renderer)
        self.volume_handler.set_renderer(ui.renderer)
        self.update = ui.update

    @abstractmethod
    def reset(self):
        pass

    @abstractmethod
    def add_volume(self, data_id, data):
        pass

    @abstractmethod
    def add_mesh(self, data_id, data):
        pass

    @abstractmethod
    def init_roi(self, roi: PlaceROILogic):
        pass

    def remove_volume(self, data_id, only_data=None):
        if self.volume_handler is None:
            return
        self.volume_handler.unregister_data(data_id, only_data)
        self.update()

    def remove_mesh(self, data_id, only_data=None):
        self.mesh_handler.unregister_data(data_id, only_data)
        self.update()
