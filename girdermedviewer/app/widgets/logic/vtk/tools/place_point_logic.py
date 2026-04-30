import logging

from trame_server import Server

from ....ui import PlacePointState, PlacePointUI, PointState
from ..views_logic import ViewsLogic
from .base_tool_logic import BaseToolLogic

logger = logging.getLogger(__name__)


class PlacePointLogic(BaseToolLogic[PlacePointState]):
    def __init__(self, server: Server, views_logic: ViewsLogic) -> None:
        super().__init__(server, views_logic, PlacePointState)
        

    def set_enabled(self, _enabled: bool) -> None:
        pass

    def set_ui(self, ui: PlacePointUI) -> None:
        ui.position_updated.connect(self._on_position_changed)
