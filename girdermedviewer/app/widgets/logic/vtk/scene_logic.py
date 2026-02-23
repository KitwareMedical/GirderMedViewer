import logging
from typing import Any

from trame_server import Server

from girdermedviewer.app.widgets.utils.app_utils import debounce

from ...ui.vtk.components import SliceView, ThreeDView, VtkView
from ...ui.vtk.scene_ui import (
    Preset,
    SceneObjectPropertyState,
    SceneObjectState,
    SceneObjectType,
    SceneState,
)
from ...utils import (
    get_presets,
    get_random_color,
    load_mesh,
    load_volume,
    supported_mesh_extensions,
    supported_volume_extensions,
)
from ..base_logic import BaseLogic

logger = logging.getLogger(__name__)


class SceneObject(BaseLogic[SceneState]):
    def __init__(
        self, server: Server, scene_object_id: str, views: list[VtkView], scene_object_type: SceneObjectType
    ) -> None:
        super().__init__(server, SceneState)
        self.id = scene_object_id
        self.type = scene_object_type
        self.image_data = None
        self.views: list[VtkView] = []
        self.set_views(views)

        self.set_object_state(SceneObjectState(object_type=scene_object_type, properties=SceneObjectPropertyState()))

    @property
    def object_state(self) -> SceneObjectState:
        return self._typed_state.data.objects.get(self.id)

    @property
    def object_properties(self) -> SceneObjectPropertyState:
        return self.object_state.properties

    def set_object_state(self, object_state: SceneObjectState | None) -> None:
        object_states = {**self.data.objects}
        if object_state is None:
            object_states.pop(self.id)
        else:
            object_states[self.id] = object_state
        self.data.objects = object_states
        self.state.flush()

    def _update_property(self, object_property_state: SceneObjectPropertyState) -> None:
        object_state = self.object_state
        object_state.properties = object_property_state

        self.set_object_state(object_state)

    @property
    def twod_views(self) -> list[SliceView]:
        return [view for view in self.views if isinstance(view, SliceView)]

    @property
    def threed_views(self) -> list[ThreeDView]:
        return [view for view in self.views if isinstance(view, ThreeDView)]

    def _add_to_view(self, view: VtkView) -> None:
        assert self.image_data is not None
        adder = getattr(view, f"add_{self.type.value}")
        if adder is not None:
            adder(self.image_data, self.id)

    def _remove_from_view(self, view: VtkView) -> None:
        remover = getattr(view, f"remove_{self.type.value}")
        if remover is not None:
            remover(self.id)

    def load_to_view(self) -> None:
        for view in self.views:
            self._add_to_view(view)

    def set_views(self, views: list[VtkView]) -> None:
        for view in self.views:
            if view not in views:
                self._remove_from_view(view)
        if self.image_data is not None:
            for view in views:
                if view not in self.views:
                    self._add_to_view(view)
        self.views = views


class VolumeObject(SceneObject):
    last_preset_name = "CT-Coronary-Arteries-3"

    def __init__(self, server: Server, scene_object_id: str, views: list[VtkView]) -> None:
        super().__init__(server, scene_object_id, views, SceneObjectType.VOLUME)
        self._is_primary = False
        self.volume_range: list[float] = []

    @debounce(0.05)
    def _update_opacity(self, opacity: float) -> None:
        if self._is_primary:
            return
        for view in self.twod_views:
            view.set_volume_opacity(self.id, opacity)

    @debounce(0.05)
    def _update_window_level(self, window_level_value: list[float]) -> None:
        for view in self.twod_views:
            view.set_volume_window_level_min_max(self.id, window_level_value)
            view.update()

    @debounce(0.05)
    def _update_preset(self, preset_name: str, preset_range: list[float]) -> None:
        self.last_preset_name = preset_name
        for view in self.threed_views:
            view.set_volume_preset(
                self.id,
                preset_name,
                preset_range,
            )

    def load(self, file_path: str) -> None:
        object_properties = self.object_properties
        self.image_data = load_volume(file_path)
        if self.image_data is not None:
            self.load_to_view()
            self.volume_range = self.image_data.GetScalarRange()

            # Init window level
            (object_properties.window_level.min_value, object_properties.window_level.max_value) = self.volume_range
            object_properties.window_level.value = [self.volume_range[0], self.volume_range[1]]

            # Init preset
            object_properties.preset_name = (
                self.last_preset_name or self.data.presets[0].title if len(self.data.presets) else ""
            )
            (object_properties.preset_range.min_value, object_properties.preset_range.max_value) = self.volume_range
            object_properties.preset_range.value = [self.volume_range[0], self.volume_range[1]]

            self._update_property(object_properties)

    def update_property(self, prop: str, prop_value: Any) -> None:
        object_properties = self.object_properties
        if prop == "preset_name":
            object_properties.preset_name = prop_value
            self._update_preset(prop_value, object_properties.preset_range.value)

        if prop == "preset_range":
            object_properties.preset_range.value = prop_value
            self._update_preset(object_properties.preset_name, prop_value)

        elif prop == "opacity":
            object_properties.opacity = prop_value
            self._update_opacity(prop_value)

        elif prop == "window_level":
            object_properties.window_level.value = prop_value
            self._update_window_level(prop_value)

        elif prop == "is_primary_volume":
            object_properties.is_primary_volume = prop_value
            self._is_primary = prop_value

        self._update_property(object_properties)

    def window_level_changed_in_view(self, window_level_in_view: list[float]) -> None:
        if not self._is_primary:
            return
        window_level_value = (
            window_level_in_view[1] - window_level_in_view[0] / 2,
            window_level_in_view[1] + window_level_in_view[0] / 2,
        )
        self.update_property("window_level", window_level_value)

    def auto_window_level(self) -> None:
        if not self._is_primary:
            return

        self.update_property("window_level", [self.volume_range[0], self.volume_range[1]])


class MeshObject(SceneObject):
    def __init__(self, server: Server, scene_object_id: str, views: list[VtkView]) -> None:
        super().__init__(server, scene_object_id, views, SceneObjectType.MESH)

    @debounce(0.05)
    def _update_opacity(self, opacity: float) -> None:
        for view in self.views:
            view.set_mesh_opacity(self.id, opacity)

    @debounce(0.05)
    def _update_color(self, color: str) -> None:
        hex = color.lstrip("#")
        color_tuple = tuple(float(int(hex[i : i + 2], 16)) / 255.0 for i in (0, 2, 4))
        for view in self.views:
            view.set_mesh_color(self.id, color_tuple)

    def load(self, file_path: str) -> None:
        object_properties = self.object_properties
        self.image_data = load_mesh(file_path)
        self.load_to_view()

        object_properties.color = get_random_color()
        self._update_color(object_properties.color)

        object_properties.opacity = 0.8
        self._update_opacity(object_properties.opacity)

        self._update_property(object_properties)

    def update_property(self, prop: str, prop_value: Any) -> None:
        object_properties = self.object_properties
        if prop == "opacity":
            object_properties.opacity = prop_value
            self._update_opacity(prop_value)

        elif prop == "color":
            object_properties.color = prop_value
            self._update_color(prop_value)

        self._update_property(object_properties)


class SceneLogic(BaseLogic[SceneState]):
    def __init__(self, server: Server) -> None:
        super().__init__(server, SceneState)
        self.scene_objects: dict[str, VolumeObject | MeshObject] = {}
        self._init_presets()

        self.primary_volume_id: str | None = None

        self.views: list[VtkView] = []

    def _init_presets(self) -> None:
        self.data.presets = [Preset(title=preset["name"], props={}) for preset in get_presets()]

    def _get_scene_object(self, file_path: str, object_id: str) -> MeshObject | VolumeObject:
        """Determines type based on file extension and upgrades the object."""
        # Upgrade object dynamically
        if file_path.endswith(supported_mesh_extensions()):
            return MeshObject(self.server, object_id, self.views)
        if file_path.endswith(supported_volume_extensions()):
            return VolumeObject(self.server, object_id, self.views)
        raise ValueError("Unsupported file extension")

    def _set_primary_volume(self) -> None:
        primary_volume = next((obj for obj in self.scene_objects.values() if isinstance(obj, VolumeObject)), None)

        if primary_volume is not None:
            primary_volume.update_property("is_primary_volume", True)
            self.primary_volume_id = primary_volume.id
        else:
            self.primary_volume_id = None

    def add_scene_object(self, file_path: str, object_id: str) -> None:
        scene_object: MeshObject | VolumeObject = self._get_scene_object(file_path, object_id)
        self.scene_objects[scene_object.id] = scene_object
        scene_object.load(file_path)

        if self.primary_volume_id is None:
            self._set_primary_volume()

    def remove_scene_object(self, object_id: str) -> None:
        scene_object = self.scene_objects.get(object_id)

        if scene_object is not None:
            scene_object.set_object_state(None)
            scene_object.set_views([])
            self.scene_objects.pop(scene_object.id)

        if object_id == self.primary_volume_id:
            self._set_primary_volume()

    def update_object_property(self, prop: str, prop_value: Any, object_id: str) -> None:
        scene_object = self.scene_objects.get(object_id)
        if scene_object:
            scene_object.update_property(prop, prop_value)

    def set_views(self, views: list[VtkView]) -> None:
        self.views = views
        for view in views:
            if isinstance(view, SliceView):
                # Connect window leveling for all slice views
                view.window_level_changed.connect(self._on_window_level_changed_in_view)

    def _on_window_level_changed_in_view(self, window_level: list[float]) -> None:
        if self.primary_volume_id is not None:
            scene_object = self.scene_objects.get(self.primary_volume_id)
            if scene_object and isinstance(scene_object, VolumeObject):
                scene_object.window_level_changed_in_view(window_level)

    def _on_auto_window_level_clicked(self) -> None:
        if self.primary_volume_id is not None:
            scene_object = self.scene_objects.get(self.primary_volume_id)
            if scene_object and isinstance(scene_object, VolumeObject):
                scene_object.auto_window_level()
