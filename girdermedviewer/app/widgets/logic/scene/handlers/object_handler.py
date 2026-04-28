import logging
from abc import abstractmethod
from pathlib import Path

from trame_server.core import Server

from ....ui import SceneState
from ...base_logic import BaseLogic
from ...vtk.views_logic import ViewsLogic
from ..objects.scene_object_logic import SceneObjectLogic

logger = logging.getLogger(__name__)


class ObjectHandler(BaseLogic[SceneState]):
    def __init__(self, server: Server, views_logic: ViewsLogic):
        super().__init__(server, SceneState)
        self.object_logics: dict[str, SceneObjectLogic] = {}
        self.views_logic = views_logic

    @property
    @abstractmethod
    def supported_extensions(self) -> tuple[str]:
        pass

    def supports_file(self, file_path: Path) -> None:
        return file_path.endswith(self.supported_extensions)

    @abstractmethod
    def add_object_to_views(self, object_logic: SceneObjectLogic) -> None:
        pass

    @abstractmethod
    def remove_object_from_views(self, object_logic: SceneObjectLogic) -> None:
        pass

    @abstractmethod
    def unregister_object_from_views(self, object_logic: SceneObjectLogic) -> None:
        pass

    def set_object_visibility(self, object_logic: SceneObjectLogic, visible: bool) -> None:
        object_logic.display.is_visible = visible
