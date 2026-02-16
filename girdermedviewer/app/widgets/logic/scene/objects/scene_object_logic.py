import logging

from trame_dataclass.v2 import (
    ClientOnly,
    FieldEncoder,
    StateDataModel,
    Sync,
    get_instance,
)
from trame_server import Server

from ....ui import (
    SliceView,
    ThreeDView,
    VtkView,
)
from ....utils import SceneObjectType
from ...base_logic import BaseLogic

logger = logging.getLogger(__name__)

DEFAULT_COLOR_PRESET_NAME = "Grayscale"

class ColorPreset(StateDataModel):
    name = Sync(str, DEFAULT_COLOR_PRESET_NAME)
    is_inverted = Sync(bool, False)


class SceneObjectInfo(StateDataModel):
    created = Sync(str)
    updated = Sync(str)
    size = Sync(str)


class SceneObjectMetadata(StateDataModel):
    meta = Sync(dict[str | str] | None)
    parent_meta = Sync(dict[str | str] | None)


class SceneObjectGUI(StateDataModel):
    current_window = ClientOnly(str)
    loading = Sync(bool, True)


class SceneObject(StateDataModel):
    name = Sync(str)
    gui = Sync(SceneObjectGUI, has_dataclass=True)
    database_id = Sync(str)
    object_type = Sync(
        SceneObjectType,
        SceneObjectType.UNDEFINED,
        convert=FieldEncoder(SceneObjectType.encoder, SceneObjectType.decoder),
    )
    info = Sync(SceneObjectInfo, has_dataclass=True)
    metadata = Sync(SceneObjectMetadata, has_dataclass=True)
    display = Sync(str)


class SceneObjectLogic(BaseLogic[None]):
    def __init__(
        self,
        server: Server,
        scene_object: SceneObject,
        views: list[VtkView],
    ) -> None:
        super().__init__(server, None)
        self.scene = get_instance(self.state.scene_id)
        self.scene_object = scene_object
        self.object_data = None
        self.views = views
        self.set_views(views)

    @property
    def twod_views(self) -> list[SliceView]:
        return [view for view in self.views if isinstance(view, SliceView)]

    @property
    def threed_views(self) -> list[ThreeDView]:
        return [view for view in self.views if isinstance(view, ThreeDView)]

    def is_volume(self) -> bool:
        return self.scene_object.object_type == SceneObjectType.VOLUME

    def is_mesh(self) -> bool:
        return self.scene_object.object_type == SceneObjectType.MESH

    def _add_to_view(self, view: VtkView) -> None:
        assert self.object_data is not None
        adder = getattr(view, f"add_{self.scene_object.object_type.value}")
        if adder is not None:
            adder(self.object_data, self.scene_object._id)

    def _remove_from_view(self, view: VtkView) -> None:
        remover = getattr(view, f"remove_{self.scene_object.object_type.value}")
        if remover is not None:
            remover(self.scene_object._id)

    def load_to_view(self) -> None:
        for view in self.views:
            self._add_to_view(view)

    def set_views(self, views: list[VtkView]) -> None:
        for view in self.views:
            if view not in views:
                self._remove_from_view(view)
        if self.object_data is not None:
            for view in views:
                if view not in self.views:
                    self._add_to_view(view)
        self.views = views
