from ....ui import SliceView, ThreeDView, ViewUI, VtkView
from ....utils import VolumePriorityType, debounce
from ..objects.volume_object_logic import VolumeObjectLogic
from .object_handler import ObjectHandler


class VolumeDisplayHandler:
    def __init__(self):
        self.views: list[VtkView] = []

    @property
    def twod_views(self) -> list[SliceView]:
        return [view for view in self.views if isinstance(view, SliceView)]

    @property
    def threed_views(self) -> list[ThreeDView]:
        return [view for view in self.views if isinstance(view, ThreeDView)]

    def update_opacity(self, volume_id: str):
        @debounce(0.05)
        def _update_opacity(opacity: float) -> None:
            if opacity < 0:
                return
            for view in self.twod_views:
                view.set_volume_opacity(volume_id, opacity)

        return _update_opacity

    def update_threed_preset(self, volume_id: str):
        @debounce(0.05)
        def _update_threed_preset(volume_preset_name: str, volume_preset_vr_shift: list[float]) -> None:
            for view in self.threed_views:
                view.set_volume_preset(
                    volume_id,
                    volume_preset_name,
                    volume_preset_vr_shift,
                )

        return _update_threed_preset

    def update_window_level(self, volume_id: str) -> None:
        @debounce(0.05)
        def _update_window_level(window_level: list[float]) -> None:
            for view in self.twod_views:
                view.set_volume_window_level_min_max(volume_id, window_level)
                view.update()

        return _update_window_level

    def set_view_ui(self, view_ui: ViewUI):
        self.views = view_ui.views


class VolumeHandler(ObjectHandler):
    object_logics: dict[str, VolumeObjectLogic] = dict

    def __init__(self, server):
        super().__init__(server)
        self.display_handler = VolumeDisplayHandler()

    @property
    def active_primary_volume_id(self) -> str | None:
        return self.data.active_primary_volume_id

    @property
    def primary_volume_ids(self) -> list[str]:
        return self.data.primary_volume_ids

    def _is_active_volume(self, volume_id: str) -> None:
        return volume_id == self.active_primary_volume_id

    def _is_primary_volume(self, volume_id: str) -> None:
        return volume_id in self.primary_volume_ids

    def _set_active_primary_volume_id(self, volume_id: str | None) -> None:
        if self.active_primary_volume_id is not None:
            super().set_object_visibility(self.object_logics.get(self.active_primary_volume_id), False)

        self.active_primary_volume_id = volume_id
        if self.active_primary_volume_id:
            super().set_object_visibility(self.object_logics.get(volume_id), True)

    def _connect_volume_to_display_handler(self, volume_logic: VolumeObjectLogic):
        volume_logic.display.watch(("opacity",), self.display_handler.update_opacity)
        volume_logic.display.watch(("window_level",), self.display_handler.update_window_level)
        volume_logic.display.threed_preset.watch(("name", "vr_shift"), self.display_handler.update_threed_preset)

    def _add_volume_to_views(self, volume_logic: VolumeObjectLogic, priority: VolumePriorityType) -> None:
        for view in self.views:
            view.add_volume(volume_logic._id, volume_logic.object_data, priority)

        if priority == VolumePriorityType.PRIMARY:
            self.primary_volume_ids.append(volume_logic._id)
            self._set_active_primary_volume_id(volume_logic._id)

    def _reload_as_primary_volume(self, volume_logic: VolumeObjectLogic) -> None:
        super().remove_object_from_views(volume_logic)
        self._add_volume_to_views(volume_logic, VolumePriorityType.PRIMARY)

    def _reload_as_secondary_volume(self, volume_logic: VolumeObjectLogic) -> None:
        super().remove_object_from_views(volume_logic)
        self.primary_volume_ids.pop(volume_logic._id)
        self._add_volume_to_views(volume_logic, VolumePriorityType.SECONDARY)

    def _get_next_volume(self, volume_logic: VolumeObjectLogic) -> tuple[str, bool]:
        next_volume_id = volume_logic.parent_id or volume_logic.soft_parent_id

        if self._is_primary_volume(next_volume_id):
            return next_volume_id, True  # primary parent

        for vol_id, vol in self.object_logics.items():
            if vol.soft_parent_logic_id == volume_logic._id:
                if self._is_primary_volume(vol._id):
                    return vol_id, True  # primary child
                if next_volume_id is None:
                    next_volume_id = vol_id

        if len(self.primary_volume_ids) > 0:
            return self.primary_volume_ids[0], True  # any primary volume

        if next_volume_id is not None:
            return next_volume_id, False  # parent or child

        return next(iter(self.object_logics), None), False  # any volume or None

    def add_object_to_views(self, volume_logic: VolumeObjectLogic) -> None:
        self.object_logics[volume_logic._id] = volume_logic
        self._connect_volume_to_display_handler(volume_logic)
        priority = (
            volume_logic.priority or VolumePriorityType.PRIMARY
            if not self.active_primary_volume_id
            else VolumePriorityType.SECONDARY
        )

        self._add_volume_to_views(volume_logic, priority)

    def remove_object_from_views(self, volume_logic: VolumeObjectLogic) -> None:
        self.object_logics.pop(volume_logic._id)
        volume_logic.display.clear_watchers()
        super().remove_object_from_views(volume_logic)

        if volume_logic._id in self.primary_volume_ids:
            self.primary_volume_ids.pop(volume_logic._id)

        if volume_logic == self.active_primary_volume_id:
            next_volume_id, is_next_volume_primary = self._get_next_volume(volume_logic)
            if is_next_volume_primary:
                self._set_active_primary_volume_id(next_volume_id)
        else:
            next_volume_logic = self.object_logics.get(next_volume_id)
            self._reload_as_primary_volume(next_volume_logic)

    def set_object_visibility(self, volume_logic: VolumeObjectLogic, visible: bool) -> None:
        if self._is_primary_volume(volume_logic) and visible:
            # Maximum one primary volume visible at a time
            self._set_active_primary_volume_id(volume_logic._id)
        else:
            super().set_object_visibility(volume_logic, visible)

    def set_object_as_overlay(self, volume_logic: VolumeObjectLogic, overlay: bool) -> None:
        if overlay:
            if (
                self._is_primary_volume(volume_logic)
                or volume_logic.priority == VolumePriorityType.PRIMARY
                or self._is_active_volume(volume_logic._id)
            ):
                return
            self._reload_as_secondary_volume(self, volume_logic)
        else:
            if self._is_primary_volume(volume_logic) or volume_logic.priority == VolumePriorityType.SECONDARY:
                return
            self._reload_as_primary_volume(self, volume_logic)

    def update_window_level(self, window_level: list[float]) -> None:
        if self.active_primary_volume_id is not None:
            object_logic = self.object_logics.get(self.active_primary_volume_id)
            if object_logic is not None:
                object_logic.window_level_changed_in_view(window_level)

    def set_view_ui(self, view_ui: ViewUI) -> None:
        super().set_view_ui(view_ui)
        for view in self.views:
            if isinstance(view, SliceView):
                view.window_level_changed.connect(self.update_window_level)
