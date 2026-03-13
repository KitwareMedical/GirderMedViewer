from abc import abstractmethod

from trame_server.core import Server

from ....ui import SceneState, ViewUI, VtkView
from ...base_logic import BaseLogic
from ..objects.scene_object_logic import SceneObjectLogic


class ObjectHandler(BaseLogic[SceneState]):
    def __init__(self, server: Server):
        super().__init__(server, SceneState)
        self.display_handler = None
        self.views: list[VtkView] = []

    @abstractmethod
    def add_object_to_views(self, object_logic: SceneObjectLogic) -> None:
        pass

    @abstractmethod
    def set_object_visibility(self, object_logic: SceneObjectLogic, visible: bool) -> None:
        pass

    def remove_object_from_views(self, object_logic: SceneObjectLogic) -> None:
        for view in self.views:
            view.unregister_data(object_logic._id)

    def set_view_ui(self, view_ui: ViewUI):
        self.views = view_ui.views
