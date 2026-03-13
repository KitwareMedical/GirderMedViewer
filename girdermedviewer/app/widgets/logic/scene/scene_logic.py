import logging

from trame_dataclass.v2 import StateDataModel, Sync
from trame_server import Server
from undo_stack import Signal

from ...ui import (
    SceneState,
    SceneUI,
    ViewUI,
    VtkView,
)
from ...utils import (
    FilterType,
    Preset,
    PresetParser,
    get_volume_preset_parser,
    supported_mesh_extensions,
    supported_volume_extensions,
)
from ..base_logic import BaseLogic
from .filters import FILTER_MAP
from .handlers.mesh_handler import MeshHandler
from .handlers.object_handler import ObjectHandler
from .handlers.volume_handler import VolumeHandler
from .objects.mesh_object_logic import MeshObjectLogic
from .objects.scene_object_logic import SceneObject, SceneObjectGUI, SceneObjectLogic
from .objects.volume_object_logic import VolumeObjectLogic

logger = logging.getLogger(__name__)


class SceneGUI(StateDataModel):
    expanded_objects = Sync(list[str], list)


class Scene(StateDataModel):
    volume_presets = Sync(list[Preset], list, has_dataclass=True)
    objects = Sync(list[SceneObject], list, has_dataclass=True)
    gui = Sync(SceneGUI, has_dataclass=True)


class SceneLogic(BaseLogic[SceneState]):
    object_added_to_views = Signal(str, bool)
    object_removed_from_views = Signal(str, bool)
    object_added = Signal(str)
    object_removed = Signal(str)
    object_load_canceled = Signal(str)

    def __init__(self, server: Server) -> None:
        super().__init__(server, SceneState)

        self.scene = Scene(self.server, gui=SceneGUI(self.server, gui=SceneGUI(self.server)))
        self.data.scene_id = self.scene._id
        self.object_logics: dict[str, SceneObjectLogic] = {}
        self._init_presets()

        self.mesh_handler = MeshHandler(self.server)
        self.volume_handler = VolumeHandler(self.server)

        self.load_tasks = {}

        self.views: list[VtkView] = []

    def _get_presets_from_preset_parser(self, preset_parser: PresetParser) -> list[Preset]:
        return [
            Preset(self.server, title=name, props={"data": data})
            for name, data in preset_parser.get_presets_icons_url()
        ]

    def _get_object_handler(self, object_logic) -> ObjectHandler:
        if isinstance(object_logic, VolumeObjectLogic):
            return self.volume_handler
        return self.mesh_handler

    def _init_presets(self) -> None:
        self.volume_preset_parser = get_volume_preset_parser()
        self.scene.volume_presets = self._get_presets_from_preset_parser(self.volume_preset_parser)

    def _create_file_object_logic(self, file_path: str, scene_object: SceneObject) -> SceneObjectLogic:
        """Determines type based on file extension and upgrades the object."""
        # Upgrade object dynamically
        if file_path.endswith(supported_mesh_extensions()):
            return MeshObjectLogic(self.server, scene_object, self.views)
        if file_path.endswith(supported_volume_extensions()):
            return VolumeObjectLogic(self.server, scene_object, self.views)
        raise ValueError("Unsupported file extension")

    def _create_filter_object_logic(
        self, parent_object_logic: SceneObjectLogic, filter_type: FilterType
    ) -> SceneObjectLogic:
        filter_object_logic_type = FILTER_MAP.get(filter_type)
        if filter_object_logic_type is None:
            raise ValueError(f"No logic associated to filter type: {filter_type.value}")

        filter_object = SceneObject(
            self.server, name=f"{parent_object_logic.scene_object.name}_{filter_type.value}", filter_type=filter_type
        )
        self.add_object(filter_object)

        return filter_object_logic_type(
            original_logic=parent_object_logic,
            server=self.server,
            scene_object=filter_object,
            views=self.views,
        )

    def _cancel_load(self, object_id):
        object_logic = self.object_logics.get(object_id)
        if object_logic is not None:
            self.object_load_canceled(object_logic.scene_object.database_id)

    def _remove_dependent_objects(self, object_logic: SceneObjectLogic) -> None:
        for obj in self.object_logics.values():
            if obj.parent_id == object_logic._id:
                self.remove_object_from_views(obj._id)

    def _add_object_to_views(self, object_logic: SceneObjectLogic) -> None:
        self._get_object_handler(object_logic).add_object_to_views()

    def _remove_object_from_views(self, object_logic: SceneObjectLogic) -> None:
        self._remove_dependent_objects(object_logic)
        self._get_object_handler(object_logic).remove_object_from_views()

    def add_object(self, scene_object: SceneObject) -> None:
        scene_object.gui = SceneObjectGUI(self.server)
        self.scene.objects = [*self.scene.objects, scene_object]
        self.object_added(scene_object._id)

    def add_file_object_to_views(self, file_path: str, object_db_id: str) -> None:
        # Check that object has been created
        scene_object = next((obj for obj in self.scene.objects if obj.database_id == object_db_id), None)
        if scene_object is not None:
            object_logic = self._create_file_object_logic(file_path, scene_object)
            self.object_logics[scene_object._id] = object_logic

            object_logic.load_object_data(file_path)
            self._add_object_to_views(object_logic)

            self.object_added_to_views(scene_object._id, len(self.scene.objects) > 0)

            self.state.flush()  # FIXME: need to flush manually
        else:
            self.object_removed(object_db_id)

    def add_filter_object_to_views(self, parent_object_id: str, filter_type: FilterType) -> None:
        parent_object_logic = self.object_logics.get(parent_object_id)
        if parent_object_logic is None:
            return

        filter_object_logic = self._create_filter_object_logic(parent_object_logic, filter_type)
        self.object_logics[filter_object_logic._id] = filter_object_logic

        self._add_object_to_views(filter_object_logic)

        self.object_added_to_views(filter_object_logic._id, len(self.scene.objects) > 0)

        self.state.flush()  # FIXME: need to flush manually

    def remove_object_from_views(self, object_id: str) -> None:
        object_logic = self.object_logics.get(object_id)

        if object_logic is not None:
            self.object_logics.pop(object_id)

        self.object_removed_from_views(object_id, len(self.scene.objects) > 0)

    def remove_object(self, object_id: str) -> None:
        object_logic = self.object_logics.get(object_id)
        if object_logic is None:
            return
        self.scene.objects = [obj for obj in self.scene.objects if obj._id != object_id]
        self.remove_object_from_views(object_id)

        if object_logic.scene_object.database_id is not None:
            self.object_removed(object_logic.scene_object.database_id)

    def set_view_ui(self, view_ui: ViewUI) -> None:
        self.volume_handler.set_view_ui(view_ui)
        self.mesh_handler.set_view_ui(view_ui)

        for view in view_ui.views:
            view.set_volume_preset_parser(self.volume_preset_parser)

    def clear_scene(self):
        object_ids = [obj._id for obj in self.scene.objects]
        for object_id in object_ids:
            self.remove_object(object_id)

    def set_ui(self, ui: SceneUI):
        ui.delete_clicked.connect(self.remove_object)
        ui.load_canceled.connect(self._cancel_load)
        ui.filter_clicked.connect(self._create_filter_object_logic)
