from trame.decorators import TrameApp, controller, change

from .vtk.components import SliceView, ThreeDView
from .vtk.utils import (
    get_random_color,
    load_mesh,
    load_volume,
    supported_volume_extensions
)


@TrameApp()
class Scene:
    def __init__(self, server):
        self.server = server
        self.ctrl.load_file = self.load_file
        self.objects = []
        self.views = []

    @property
    def state(self):
        return self.server.state

    @property
    def ctrl(self):
        return self.server.controller

    def get_object(self, id):
        return next((object for object in self.objects if object.id == id), None)

    @change("selected")
    def on_selected_changed(self, selected, **kwargs):
        for item_id in selected.keys():
            object = self.get_object(item_id)
            if object is None:
                object = SceneObject(self.server, item_id, None, self.views)
                self.objects.append(object)

    @controller.set("load_file")
    def load_file(self, file_path, data_id=None):
        # find object created when added to "selected"
        obj = self.get_object(data_id)
        if obj:
            upgraded_obj = obj.set_file_path(file_path)
            # Note: Make sure that reset() is not called here (existing object is being deleted)
            self.objects[self.objects.index(obj)] = upgraded_obj
            del obj
            upgraded_obj.load(file_path)

    @controller.set("clear")
    def clear(self):
        self.objects.clear()

    @controller.set("add_view")
    def add_view(self, view):
        self.views.append(view)
        self.set_views(self.views)

    @controller.set("remove_view")
    def remove_view(self, view):
        self.views.remove(view)
        self.set_views(self.views)

    def set_views(self, views):
        self.views = views
        for object in self.objects:
            object.set_views(self.views)


@TrameApp()
class SceneObject:
    def __init__(self, server, id, data_type, views):
        self.server = server
        self.id = id
        self.data = None
        self.views = []
        self.set_views(views)

        self.state[id] = {
            "id": id,
            "type": data_type,
            "opacity": 1.0,
            "loaded": False,
        }
        self.state.dirty(id)

    def __del__(self):
        # do not reset when specializing the class
        if self.data is not None:
            self.reset()

    def reset(self):
        """Must be reimplemted to clear data"""
        # remove self from all views
        self.set_views([])
        self.data = None
        self.id = None
        self.file_path = None

    @property
    def state(self):
        return self.server.state

    @property
    def data_type(self):
        return self.state[self.id]["type"]

    @property
    def twod_views(self):
        return [view for view in self.views if isinstance(view, SliceView)]

    @property
    def threed_views(self):
        return [view for view in self.views if isinstance(view, ThreeDView)]

    def _add_to_view(self, view):
        assert self.data is not None
        adder = getattr(view, f'add_{self.data_type}')
        if adder is not None:
            adder(self.data, self.id)

    def _remove_from_view(self, view):
        remover = getattr(view, f'remove_{self.data_type}')
        if remover is not None:
            remover(self.id)

    def set_file_path(self, file_path):
        """Determines type based on file extension and upgrades the object."""
        # Upgrade object dynamically
        if file_path.endswith(".stl"):
            return Mesh(self)
        elif file_path.endswith(supported_volume_extensions()):
            return Volume(self)
        return self

    def load(self, file_path):
        self.file_path = file_path
        for view in self.views:
            self._add_to_view(view)
        self.loaded = True

    def set_views(self, views):
        for view in self.views:
            if view not in views:
                self._remove_from_view(view)
        if self.data is not None:
            for view in views:
                if view not in self.views:
                    self._add_to_view(view)
        self.views = views

    @property
    def loaded(self):
        return self.state[self.id]["loaded"]

    @loaded.setter
    def loaded(self, value):
        self.state[self.id]["loaded"] = value
        self.state.dirty(self.id)

    @property
    def opacity(self):
        return self.state[self.id]["opacity"]

    @opacity.setter
    def opacity(self, value):
        self.state[self.id]["opacity"] = value
        self.state.dirty(self.id)


class Volume(SceneObject):
    last_preset_name = None

    def __init__(self, scene_object):
        super().__init__(scene_object.server, scene_object.id, 'volume', scene_object.views)
        self.state.change(self.id)(self._on_change)

    def load(self, file_path):
        self.data = load_volume(file_path)

        scalar_range = self.data.GetScalarRange()
        self.scalar_range = scalar_range
        self.window_level_min_max = scalar_range
        self.preset_name = (
            Volume.last_preset_name or self.state.presets[0].get('name')
            if len(self.state.presets) else None)
        self.preset_range = scalar_range

        self._on_change()
        super().load(file_path)

    def _add_to_view(self, view):
        super()._add_to_view(view)
        if self.is_primary():
            self.opacity = -1
        self.state[self.id]["is_secondary"] = not self.is_primary()
        self.state.dirty(self.id)

    def _on_change(self, *_, **kwargs):
        self._on_opacity_change(_, **kwargs)
        self._on_window_level_change(_, **kwargs)
        self._on_preset_change(_, **kwargs)

    def _on_opacity_change(self, *_, **kwargs):
        for view in self.twod_views:
            view.set_volume_opacity(self.id, self.opacity)

    def is_primary(self):
        for view in self.twod_views:
            if view.is_primary_volume(self.id):
                return True
        return False

    @property
    def scalar_range(self):
        return (self.state[self.id]["range_min"], self.state[self.id]["range_max"])

    @scalar_range.setter
    def scalar_range(self, value):
        self.state[self.id]["range_min"] = value[0]
        self.state[self.id]["range_max"] = value[1]
        self.state.dirty(self.id)

    @property
    def window_level_min_max(self):
        return self.state[self.id]["window_level_min_max"]

    @window_level_min_max.setter
    def window_level_min_max(self, value):
        self.state[self.id]["window_level_min_max"] = value
        self.state.dirty(self.id)

    def _on_window_level_change(self, *_, **kwargs):
        for view in self.twod_views:
            view.set_volume_window_level_min_max(
                self.id,
                self.window_level_min_max
            )

    @controller.add("window_level_changed_in_view")
    def window_level_changed_in_view(self, window_level):
        if not self.is_primary:
            return
        min_max = (
            window_level[1] - window_level[0] / 2,
            window_level[1] + window_level[0] / 2)
        self.window_level_min_max = min_max
        self.state.flush()

    @property
    def preset_name(self):
        return self.state[self.id]["preset"]

    @preset_name.setter
    def preset_name(self, value):
        self.state[self.id]["preset"] = value
        self.state.dirty(self.id)

    @property
    def preset_range(self):
        return (
            float(self.state[self.id]["preset_min"]),
            float(self.state[self.id]["preset_max"]))

    @preset_range.setter
    def preset_range(self, value):
        self.state[self.id]["preset_min"] = value[0]
        self.state[self.id]["preset_max"] = value[1]
        self.state.dirty(self.id)

    def _on_preset_change(self, *_, **kwargs):
        # FIXME use self.context ?
        Volume.last_preset_name = self.preset_name
        for view in self.threed_views:
            view.set_volume_preset(
                self.id,
                self.preset_name,
                self.preset_range
            )


class Mesh(SceneObject):

    def __init__(self, scene_object):
        super().__init__(scene_object.server, scene_object.id, 'mesh', scene_object.views)
        # FIXME move to superclass
        self.state.change(self.id)(self._on_change)

    def load(self, file_path):
        self.data = load_mesh(file_path)
        self.color = get_random_color()
        self._on_change()
        super().load(file_path)

    def _on_change(self, *_, **kwargs):
        self._on_opacity_change(_, **kwargs)
        self._on_color_change(_, **kwargs)

    def _on_opacity_change(self, *_, **kwargs):
        for view in self.views:
            view.set_mesh_opacity(self.id, self.opacity)

    @property
    def color(self):
        return self.state[self.id]["color"]

    @color.setter
    def color(self, value):
        self.state[self.id]["color"] = value
        self.state.dirty(self.id)

    def _on_color_change(self, *_, **kwargs):
        hex = self.color.lstrip("#")
        c = tuple(float(int(hex[i: i + 2], 16)) / 255. for i in (0, 2, 4))
        for view in self.views:
            view.set_mesh_color(
                self.id,
                c
            )
