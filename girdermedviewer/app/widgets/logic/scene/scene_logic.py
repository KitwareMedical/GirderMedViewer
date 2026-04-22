import logging

from trame_dataclass.v2 import StateDataModel, Sync, get_instance
from trame_server import Server
from undo_stack import Signal

from ...ui import SceneState, SceneUI
from ...utils import (
    FilterType,
    Preset,
    PresetParser,
)
from ..base_logic import BaseLogic
from ..vtk.views_logic import ViewsLogic
from .filters import FILTER_MAP
from .filters.segmentation_filter_logic import SegmentationFilterLogic
from .handlers.mesh_handler import MeshHandler
from .handlers.object_handler import ObjectHandler
from .handlers.segmentation_handler import SegmentationHandler
from .handlers.volume_handler import VolumeHandler
from .objects.mesh_object_logic import MeshObjectLogic
from .objects.scene_object_logic import SceneObject, SceneObjectGUI, SceneObjectLogic
from .objects.volume_object_logic import VolumeObjectLogic

logger = logging.getLogger(__name__)


class SceneGUI(StateDataModel):
    expanded_object = Sync(str, list)


class Scene(StateDataModel):
    volume_presets = Sync(list[Preset], list, has_dataclass=True)
    color_presets = Sync(list[Preset], list, has_dataclass=True)
    objects = Sync(list[SceneObject], list, has_dataclass=True)
    gui = Sync(SceneGUI, has_dataclass=True)


class SceneLogic(BaseLogic[SceneState]):
    object_added = Signal(str)
    object_removed = Signal(str, str)
    object_load_canceled = Signal(str)

    def __init__(self, server: Server, views_logic: ViewsLogic) -> None:
        super().__init__(server, SceneState)

        self.scene = Scene(self.server, gui=SceneGUI(self.server))
        self.data.scene_id = self.scene._id
        self.object_logics: dict[str, SceneObjectLogic] = {}
        self._init_presets(views_logic)

        self.mesh_handler = MeshHandler(self.server, views_logic)
        self.volume_handler = VolumeHandler(self.server, views_logic)
        self.segmentation_handler = SegmentationHandler(self.server, views_logic)

    def _get_presets_from_preset_parser(self, preset_parser: PresetParser) -> list[Preset]:
        return [
            Preset(self.server, title=name, props={"data": data})
            for name, data in preset_parser.get_presets_icons_url()
        ]

    def _get_object_handler(self, object_logic) -> ObjectHandler:
        if isinstance(object_logic, SegmentationFilterLogic):
            return self.segmentation_handler
        if isinstance(object_logic, VolumeObjectLogic):
            return self.volume_handler
        return self.mesh_handler

    def _init_presets(self, views_logic: ViewsLogic) -> None:
        self.scene.volume_presets = self._get_presets_from_preset_parser(views_logic.volume_preset_parser)
        self.scene.color_presets = self._get_presets_from_preset_parser(views_logic.color_preset_parser)

    def _create_file_object_logic(
        self, file_path: str, scene_object: SceneObject
    ) -> MeshObjectLogic | VolumeObjectLogic:
        """Determines type based on file extension and upgrades the object."""
        # Upgrade object dynamically
        if self.mesh_handler.supports_file(file_path):
            return MeshObjectLogic(self.server, scene_object)
        if self.volume_handler.supports_file(file_path):
            return VolumeObjectLogic(self.server, scene_object)
        raise ValueError("Unsupported file extension")

    def _create_filter_object_logic(
        self, input_object_logic: SceneObjectLogic, filter_type: FilterType
    ) -> SceneObjectLogic:
        filter_object_logic_type = FILTER_MAP.get(filter_type)
        if filter_object_logic_type is None:
            raise ValueError(f"No logic associated to filter type: {filter_type.value}")

        filter_object = SceneObject(
            self.server, name=f"{input_object_logic.scene_object.name}_{filter_type.value}", filter_type=filter_type
        )
        self.add_object(filter_object)

        return filter_object_logic_type(
            original_logic=input_object_logic,
            server=self.server,
            scene_object=filter_object,
        )

    def _cancel_load(self, object_id: str) -> None:
        scene_object = next((obj for obj in self.scene.objects if obj._id == object_id), None)
        if scene_object is not None:
            self.object_load_canceled(object_id)
        else:
            logger.debug(f"Scene object {object_id} does not exist.")

    def _remove_object_from_views(self, object_id: str, is_dependent: bool = False) -> None:
        object_logic = self.object_logics.get(object_id)
        if object_logic is None:
            return

        self.object_logics.pop(object_id)
        object_handler = self._get_object_handler(object_logic)
        if is_dependent:
            object_handler.unregister_object_from_views(object_logic)
        else:
            object_handler.remove_object_from_views(object_logic)

    def _remove_object(self, object_id: str) -> None:
        scene_object = get_instance(object_id)
        self.scene.objects = [obj for obj in self.scene.objects if obj != scene_object]
        if not isinstance(scene_object, SceneObject):
            logger.debug(f"Id {object_id} does not match a SceneObject.")
            return
        if scene_object.database_id is not None:
            self.object_removed(object_id, scene_object.database_id)

    def _get_dependent_objects(self, object_id: str) -> None:
        dependent_objects = []
        for obj in self.object_logics.values():
            if obj.input_id == object_id:
                dependent_objects += [obj._id, *self._get_dependent_objects(obj._id)]
        return dependent_objects

    def _remove_dependent_objects(self, object_id: str) -> None:
        for obj_id in self._get_dependent_objects(object_id):
            self._remove_object_from_views(obj_id, is_dependent=True)
            self._remove_object(obj_id)

    def _add_object_to_views(self, object_logic: SceneObjectLogic) -> None:
        self._get_object_handler(object_logic).add_object_to_views(object_logic)
        object_logic.set_loading_status(False)
        object_logic.set_icon()
        self.scene.gui.expanded_object = object_logic._id

        self.object_logics[object_logic._id] = object_logic

    def _add_segment(self, seg_filter_logic_id: str) -> None:
        seg_filter_logic = self.object_logics.get(seg_filter_logic_id)
        if not isinstance(seg_filter_logic, SegmentationFilterLogic):
            return
        self.segmentation_handler.add_segment_to_labelmap(seg_filter_logic)

    def _delete_segment(self, seg_filter_logic_id: str, deleted_segment_id: str) -> None:
        seg_filter_logic = self.object_logics.get(seg_filter_logic_id)
        if not isinstance(seg_filter_logic, SegmentationFilterLogic):
            return
        self.segmentation_handler.delete_segment_from_labelmap(seg_filter_logic, deleted_segment_id)

    def _select_segment(self, seg_filter_logic_id: str, selected_segment_id: str) -> None:
        seg_filter_logic = self.object_logics.get(seg_filter_logic_id)
        if not isinstance(seg_filter_logic, SegmentationFilterLogic):
            return
        self.segmentation_handler.select_segment_in_labelmap(seg_filter_logic, selected_segment_id)

    def add_object(self, scene_object: SceneObject) -> None:
        scene_object.gui = SceneObjectGUI(self.server)
        if scene_object in self.scene.objects:
            logger.debug(f"Scene object {scene_object._id} already exists.")
            return
        self.scene.objects = [*self.scene.objects, scene_object]
        self.object_added(scene_object._id)

    def add_file_object_to_views(self, file_path: str, object_id: str) -> None:
        # Check that object has been created
        scene_object: SceneObject = next((obj for obj in self.scene.objects if obj._id == object_id), None)
        if scene_object is not None:
            object_logic = self._create_file_object_logic(file_path, scene_object)
            object_logic.load_object_data(file_path)

            self._add_object_to_views(object_logic)
        else:
            self.object_removed(object_id, scene_object.database_id)

    def add_filter_object_to_views(self, input_object_id: str, filter_type: FilterType) -> None:
        input_object_logic = self.object_logics.get(input_object_id)
        if input_object_logic is None:
            return

        filter_object_logic = self._create_filter_object_logic(input_object_logic, filter_type)

        self._add_object_to_views(filter_object_logic)

    def remove_object(self, object_id: str) -> None:
        self._remove_dependent_objects(object_id)
        self._remove_object_from_views(object_id)
        self._remove_object(object_id)

    def toggle_object_visibility(self, object_id: str) -> None:
        object_logic = self.object_logics.get(object_id)
        if object_logic is None:
            return

        self._get_object_handler(object_logic).set_object_visibility(
            object_logic, not object_logic.scene_object.is_visible
        )

    def toggle_object_overlay(self, object_id: str) -> None:
        object_logic = self.object_logics.get(object_id)
        if object_logic is None or not isinstance(object_logic, VolumeObjectLogic):
            return

        self.volume_handler.toggle_object_overlay(object_logic)

    def clear_scene(self):
        object_ids = [obj._id for obj in self.scene.objects]
        for object_id in object_ids:
            self.remove_object(object_id)

    def set_ui(self, ui: SceneUI):
        ui.delete_clicked.connect(self.remove_object)
        ui.load_canceled.connect(self._cancel_load)
        ui.filter_clicked.connect(self.add_filter_object_to_views)
        ui.visibility_clicked.connect(self.toggle_object_visibility)
        ui.overlay_clicked.connect(self.toggle_object_overlay)
        ui.add_segment_clicked.connect(self._add_segment)
        ui.delete_segment_clicked.connect(self._delete_segment)
        ui.segment_clicked.connect(self._select_segment)
