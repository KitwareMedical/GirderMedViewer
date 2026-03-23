import logging
from abc import abstractmethod

from trame_dataclass.v2 import (
    ClientOnly,
    FieldEncoder,
    StateDataModel,
    Sync,
)
from trame_server import Server
from undo_stack import Signal

from ....utils import FilterType, SceneObjectType
from ...base_logic import BaseLogic

logger = logging.getLogger(__name__)

DEFAULT_THREED_PRESET_NAME = "CT-Cardiac3"
DEFAULT_TWOD_PRESET_NAME = "Grayscale"


class ThreeDColor(StateDataModel):
    name = Sync(str, DEFAULT_THREED_PRESET_NAME)
    vr_shift = Sync(list[float], list)


class TwoDColor(StateDataModel):
    name = Sync(str, DEFAULT_TWOD_PRESET_NAME)
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
    filter_type = Sync(
        FilterType,
        FilterType.UNDEFINED,
        convert=FieldEncoder(FilterType.encoder, FilterType.decoder),
    )
    filter_prop_id = Sync(str)
    is_visible = Sync(bool, True)


class SceneObjectLogic(BaseLogic[None]):
    """
    Defines properties of object added to the scene:
        - display, info, metadata
        - VTK data
        - input

    An object can have input object:
        - input: depends on its input; if the input is deleted, then the object is also deleted
        - soft input: copied information from its input but can exist without it
    """

    updated = Signal()

    def __init__(
        self,
        server: Server,
        scene_object: SceneObject,
    ) -> None:
        super().__init__(server, None)
        self._id = scene_object._id
        self.scene_object = scene_object
        self.object_data = None
        self.input_id = None
        self.soft_input_id = None

    @abstractmethod
    def load_object_data(self, *args, **kwargs):
        pass

    def set_loading_status(self, loading: bool) -> None:
        self.scene_object.gui.loading = loading
