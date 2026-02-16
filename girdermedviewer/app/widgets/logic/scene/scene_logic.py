import logging

from trame_dataclass.v2 import StateDataModel, Sync
from trame_server import Server
from undo_stack import Signal

from ...ui import (
    SceneUI,
    SliceView,
    ThreeDView,
    ViewUI,
    VtkView,
)
from ...utils import (
    Preset,
    PresetParser,
    get_color_preset_parser,
    get_volume_preset_parser,
    supported_mesh_extensions,
    supported_volume_extensions,
)
from ..base_logic import BaseLogic
from .objects import (
    MeshObjectLogic,
    SceneObject,
    SceneObjectGUI,
    SceneObjectLogic,
    VolumeObjectLogic,
)

logger = logging.getLogger(__name__)


class SceneGUI(StateDataModel):
    expanded_objects = Sync(list[str], list)


class Scene(StateDataModel):
    volume_presets = Sync(list[Preset], list, has_dataclass=True)
    color_presets = Sync(list[Preset], list, has_dataclass=True)
    objects = Sync(list[SceneObject], list, has_dataclass=True)
    gui = Sync(SceneGUI, has_dataclass=True)


class SceneLogic(BaseLogic[None]):
    object_loaded = Signal(str, bool)
    object_unloaded = Signal(str, bool)
    object_added = Signal(str)
    object_removed = Signal(str)
    object_load_canceled = Signal(str)

    def __init__(self, server: Server) -> None:
        super().__init__(server, None)

        self.scene = Scene(self.server, gui=SceneGUI(self.server, gui=SceneGUI(self.server)))
        self.state.scene_id = self.scene._id
        self.scene_object_logics: dict[str, VolumeObjectLogic | MeshObjectLogic] = {}
        self._init_presets()

        self.primary_volumes: list[str] = []
        self.load_tasks = {}

        self.views: list[VtkView] = []

    def _get_presets_from_preset_parser(self, preset_parser: PresetParser) -> list[Preset]:
        return [
            Preset(self.server, title=name, props={"data": data})
            for name, data in preset_parser.get_presets_icons_url()
        ]

    def _init_presets(self) -> None:
        self.volume_preset_parser = get_volume_preset_parser()
        self.scene.volume_presets = self._get_presets_from_preset_parser(self.volume_preset_parser)

        self.color_preset_parser = get_color_preset_parser()
        self.scene.color_presets = self._get_presets_from_preset_parser(self.color_preset_parser)

    def _create_scene_object_logic(self, file_path: str, scene_object: SceneObject) -> MeshObjectLogic | VolumeObjectLogic:
        """Determines type based on file extension and upgrades the object."""
        # Upgrade object dynamically
        if file_path.endswith(supported_mesh_extensions()):
            return MeshObjectLogic(self.server, scene_object, self.views)
        if file_path.endswith(supported_volume_extensions()):
            return VolumeObjectLogic(self.server, scene_object, self.views)
        raise ValueError("Unsupported file extension")

    def _set_primary_volume(self, scene_object_logic: SceneObjectLogic) -> None:
        if scene_object_logic.is_volume():
            self.primary_volumes.append(scene_object_logic.scene_object._id)
            scene_object_logic.display.opacity = -1.0

    def _cancel_load(self, scene_object_id):
        scene_object_logic = self.scene_object_logics.get(scene_object_id)
        if scene_object_logic is not None:
            self.object_load_canceled(scene_object_logic.scene_object.database_id)

    def _on_window_level_changed_in_view(self, window_level: list[float]) -> None:
        if len(self.primary_volumes) > 0:
            scene_object_logic = self.scene_object_logics.get(self.primary_volumes[0])
            if scene_object_logic and isinstance(scene_object_logic, VolumeObjectLogic):
                scene_object_logic.window_level_changed_in_view(window_level)

    def add_scene_object(self, scene_object: SceneObject) -> None:
        scene_object.gui = SceneObjectGUI(self.server)
        self.scene.objects = [*self.scene.objects, scene_object]
        self.object_added(scene_object._id)

    def load_scene_object(self, file_path: str, scene_object_db_id: str) -> None:
        # Check that object has been created
        scene_object = next((obj for obj in self.scene.objects if obj.database_id == scene_object_db_id), None)
        if scene_object is not None:
            scene_object_logic: MeshObjectLogic | VolumeObjectLogic = self._create_scene_object_logic(
                file_path, scene_object
            )
            self.scene_object_logics[scene_object._id] = scene_object_logic
            scene_object_logic.load(file_path)

            if len(self.primary_volumes) == 0:
                self._set_primary_volume(scene_object_logic)

            self.object_loaded(scene_object._id, len(self.scene.objects) > 0)

            self.state.flush()  # FIXME: need to flush manually
        else:
            self.object_removed(scene_object_db_id)

    def unload_scene_object(self, scene_object_id: str) -> None:
        scene_object_logic = self.scene_object_logics.get(scene_object_id)

        if scene_object_id in self.primary_volumes:
            self.primary_volumes = [volume_id for volume_id in self.primary_volumes if volume_id != scene_object_id]

        if scene_object_logic is not None:
            scene_object_logic.set_views([])
            self.scene_object_logics.pop(scene_object_id)
        self.object_unloaded(scene_object_id, len(self.scene.objects) > 0)

    def remove_scene_object(self, scene_object_id: str) -> None:
        scene_object_logic = self.scene_object_logics.get(scene_object_id)
        if scene_object_logic is not None:
            self.scene.objects = [obj for obj in self.scene.objects if obj._id != scene_object_id]
            self.unload_scene_object(scene_object_id)
            self.object_removed(scene_object_logic.scene_object.database_id)

    def set_view_ui(self, ui: ViewUI) -> None:
        self.views = ui.views
        for view in self.views:
            if isinstance(view, SliceView):
                view.set_color_preset_parser(self.color_preset_parser)
                # Connect window leveling for all slice views
                view.window_level_changed.connect(self._on_window_level_changed_in_view)
            if isinstance(view, ThreeDView):
                view.set_color_preset_parser(self.color_preset_parser)
                view.set_volume_preset_parser(self.volume_preset_parser)

    def clear_scene(self):
        object_ids = [obj._id for obj in self.scene.objects]
        for object_id in object_ids:
            self.remove_scene_object(object_id)

    def set_ui(self, ui: SceneUI):
        ui.delete_clicked.connect(self.remove_scene_object)
        ui.load_canceled.connect(self._cancel_load)
