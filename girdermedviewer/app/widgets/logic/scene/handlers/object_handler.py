import logging
from abc import abstractmethod
from pathlib import Path

from trame_server.core import Server

from ....ui import SceneState, ViewUI, VtkView
from ...base_logic import BaseLogic
from ..objects.scene_object_logic import SceneObjectLogic

logger = logging.getLogger(__name__)


class ObjectHandler(BaseLogic[SceneState]):
    def __init__(self, server: Server):
        super().__init__(server, SceneState)
        self.object_logics: dict[str, SceneObjectLogic] = {}
        self.display_handler = None
        self.views: list[VtkView] = []

    @property
    @abstractmethod
    def supported_extensions(self) -> tuple[str]:
        pass

    @abstractmethod
    def supports_file(self, file_path: Path) -> None:
        return file_path.endswith(self.supported_extensions)

    @abstractmethod
    def add_object_to_views(self, object_logic: SceneObjectLogic) -> None:
        pass

    @abstractmethod
    def remove_object_from_views(self, object_logic: SceneObjectLogic) -> None:
        pass

    @abstractmethod
    def set_object_visibility(self, object_logic: SceneObjectLogic, visible: bool) -> None:
        pass

    def unregister_object_from_views(self, object_logic: SceneObjectLogic) -> None:
        for view in self.views:
            view.unregister_data(object_logic._id)

    def set_view_ui(self, view_ui: ViewUI):
        self.views = view_ui.views
