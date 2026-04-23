import logging
from collections.abc import Callable

from trame_server.core import Server

from ....utils import VolumeLayer, debounce, supported_volume_extensions
from ...vtk.views_logic import ViewsLogic
from ..objects.volume_object_logic import VolumeObjectLogic
from .object_handler import ObjectHandler

logger = logging.getLogger(__name__)


class VolumeDisplayHandler:
    def __init__(self, views_logic: ViewsLogic):
        self.views_logic = views_logic

    def update_visibility(self, volume_logic: VolumeObjectLogic, visible: bool) -> None:
        volume_logic.display.is_visible = visible
        for view in self.views_logic.views:
            modified = view.volume_handler.set_volume_visibility(volume_logic._id, visible)
            if modified:
                view.update()

    def update_threed_visibility(self, volume_logic: VolumeObjectLogic) -> Callable:
        def _update_threed_visibility(is_threed_visible: bool) -> None:
            if not volume_logic.is_visible:
                return
            for view in self.views_logic.threed_views:
                modified = view.volume_handler.set_volume_visibility(volume_logic._id, is_threed_visible)
                if modified:
                    view.update()

        return _update_threed_visibility

    def update_opacity(self, volume_logic: VolumeObjectLogic) -> Callable:
        @debounce(0.05)
        def _update_opacity(opacity: float) -> None:
            if opacity < 0 or not volume_logic.is_visible:
                return
            for view in self.views_logic.slice_views:
                modified = view.volume_handler.set_volume_opacity(volume_logic._id, opacity)
                if modified:
                    view.update()

        return _update_opacity

    def update_threed_coloring(self, volume_logic: VolumeObjectLogic) -> Callable:
        def _update_threed_coloring(threed_preset_name: str, threed_preset_vr_shift: list[float]) -> None:
            if not volume_logic.is_visible:
                return
            for view in self.views_logic.threed_views:
                modified = view.volume_handler.set_volume_preset(
                    volume_logic._id,
                    threed_preset_name,
                    threed_preset_vr_shift,
                )
                if modified:
                    view.update()

        return _update_threed_coloring

    def update_twod_coloring(self, volume_logic: VolumeObjectLogic) -> Callable:
        def _update_twod_coloring(twod_preset_name: str, twod_preset_is_inverted: bool) -> None:
            if not volume_logic.is_visible:
                return
            for view in self.views_logic.slice_views:
                modified = view.volume_handler.set_volume_scalar_color_preset(
                    volume_logic._id,
                    twod_preset_name,
                    twod_preset_is_inverted,
                )
                if modified:
                    view.update()

        return _update_twod_coloring

    def update_normal_coloring(self, volume_logic: VolumeObjectLogic) -> Callable:
        @debounce(0.05)
        def _update_normal_coloring(show_arrows: bool, sampling: int, arrow_length: float, arrow_width: float) -> None:
            if not volume_logic.is_visible:
                return

            for view in self.views_logic.views:
                view.volume_handler.set_volume_visibility(volume_logic._id, not show_arrows)
                modified = view.volume_handler.set_volume_normal_color(
                    volume_logic._id,
                    show_arrows,
                    sampling,
                    arrow_length,
                    arrow_width,
                )
                if modified:
                    view.update()

        return _update_normal_coloring

    def update_window_level(self, volume_logic: VolumeObjectLogic) -> Callable:
        @debounce(0.05)
        def _update_window_level(window_level: list[float]) -> None:
            if not volume_logic.is_visible:
                return
            for view in self.views_logic.slice_views:
                modified = view.volume_handler.set_volume_window_level_min_max(volume_logic._id, window_level)
                if modified:
                    view.update()

        return _update_window_level


class VolumeHandler(ObjectHandler):
    def __init__(self, server: Server, views_logic: ViewsLogic):
        super().__init__(server, views_logic)
        self._display_handler = VolumeDisplayHandler(self.views_logic)
        self.views_logic.window_level_changed.connect(self._update_active_primary_window_level)

    @property
    def active_primary_volume_id(self) -> str | None:
        return self.data.active_primary_volume_id

    @property
    def primary_volume_ids(self) -> list[str]:
        return self.data.primary_volume_ids

    @property
    def supported_extensions(self) -> tuple[str]:
        return supported_volume_extensions()

    def _update_active_primary_window_level(self, view_window_level: list[float]) -> None:
        if self.active_primary_volume_id is not None:
            object_logic = self.object_logics.get(self.active_primary_volume_id)
            if object_logic is not None:
                window_level = [
                    view_window_level[1] - view_window_level[0] / 2,
                    view_window_level[1] + view_window_level[0] / 2,
                ]
                object_logic.display.window_level = window_level

    def _is_active_volume(self, volume_id: str) -> None:
        return volume_id == self.active_primary_volume_id

    def _is_primary_volume(self, volume_id: str) -> None:
        return volume_id in self.primary_volume_ids

    def _set_active_primary_volume_id(self, volume_id: str | None) -> None:
        if self.active_primary_volume_id is not None:
            old_active = self.object_logics.get(self.active_primary_volume_id)
            if old_active is not None and old_active.is_visible:
                self._display_handler.update_visibility(old_active, False)

        self.data.active_primary_volume_id = volume_id
        if self.active_primary_volume_id is not None:
            new_active = self.object_logics.get(self.active_primary_volume_id)
            if not new_active.is_visible:
                self._display_handler.update_visibility(new_active, True)

    def _add_to_primary_volumes(self, volume_id: str) -> None:
        if not self._is_primary_volume(volume_id):
            self.data.primary_volume_ids = [*self.primary_volume_ids, volume_id]

    def _remove_from_primary_volumes(self, volume_id: str) -> None:
        self.data.primary_volume_ids = [vol_id for vol_id in self.primary_volume_ids if vol_id != volume_id]

    def _connect_volume_to_display_handler(self, volume_logic: VolumeObjectLogic):
        volume_logic.display.watch(("opacity",), self._display_handler.update_opacity(volume_logic))
        volume_logic.display.watch(("window_level",), self._display_handler.update_window_level(volume_logic))
        volume_logic.display.watch(("is_threed_visible",), self._display_handler.update_threed_visibility(volume_logic))

        if volume_logic.display.normal_color is not None:
            volume_logic.display.normal_color.watch(
                ("show_arrows", "sampling", "arrow_length", "arrow_width"),
                self._display_handler.update_normal_coloring(volume_logic),
            )
        elif volume_logic.display.twod_color is not None and volume_logic.display.threed_color is not None:
            volume_logic.display.threed_color.watch(
                ("name", "vr_shift"), self._display_handler.update_threed_coloring(volume_logic)
            )
            volume_logic.display.twod_color.watch(
                ("name", "is_inverted"), self._display_handler.update_twod_coloring(volume_logic)
            )
        volume_logic.updated.connect(self.views_logic.update_views)

    def _add_volume_to_views(self, volume_logic: VolumeObjectLogic, layer: VolumeLayer) -> None:
        if layer == VolumeLayer.PRIMARY:
            self._add_to_primary_volumes(volume_logic._id)
            self._set_active_primary_volume_id(volume_logic._id)

        elif layer == VolumeLayer.SECONDARY:
            volume_logic.display.opacity = 0.5
            volume_logic.display.is_threed_visible = False
            if not volume_logic.is_visible:
                self._display_handler.update_visibility(volume_logic, True)

        self.views_logic.add_volume(
            volume_logic._id,
            volume_logic.object_data,
            volume_logic.display,
            layer,
            volume_logic.scene_object.object_subtype,
        )

    def _reload_as_primary_volume(self, volume_logic: VolumeObjectLogic) -> None:
        self.views_logic.remove_volume(volume_logic._id)
        self._add_volume_to_views(volume_logic, VolumeLayer.PRIMARY)

    def _reload_as_secondary_volume(self, volume_logic: VolumeObjectLogic) -> None:
        self.views_logic.remove_volume(volume_logic._id)
        self._remove_from_primary_volumes(volume_logic._id)
        self._add_volume_to_views(volume_logic, VolumeLayer.SECONDARY)

    def _get_next_volume(self, volume_logic: VolumeObjectLogic) -> tuple[str, bool]:
        next_volume_id = volume_logic.input_id or volume_logic.soft_input_id

        if self._is_primary_volume(next_volume_id):
            return next_volume_id, True  # primary parent

        for vol_id, vol in self.object_logics.items():
            if vol.soft_input_id == volume_logic._id:
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
        layer = volume_logic.layer

        if layer == VolumeLayer.UNDEFINED:
            input_id = volume_logic.input_id or volume_logic.soft_input_id
            layer = (
                VolumeLayer.PRIMARY
                if self._is_primary_volume(input_id) or self.active_primary_volume_id is None
                else VolumeLayer.SECONDARY
            )

        self._add_volume_to_views(volume_logic, layer)

    def unregister_object_from_views(self, volume_logic: VolumeObjectLogic) -> None:
        volume_logic.display.clear_watchers()
        self.object_logics.pop(volume_logic._id)

        if self._is_primary_volume(volume_logic._id):
            self._remove_from_primary_volumes(volume_logic._id)

        self.views_logic.remove_volume(volume_logic._id)

    def remove_object_from_views(self, volume_logic: VolumeObjectLogic) -> None:
        self.unregister_object_from_views(volume_logic)

        if self._is_active_volume(volume_logic._id):
            next_volume_id, is_next_volume_primary = self._get_next_volume(volume_logic)
            if is_next_volume_primary or next_volume_id is None:
                self._set_active_primary_volume_id(next_volume_id)
            else:
                next_volume_logic = self.object_logics.get(next_volume_id)
                self._reload_as_primary_volume(next_volume_logic)

    def toggle_object_overlay(self, volume_logic: VolumeObjectLogic) -> None:
        if self._is_primary_volume(volume_logic._id):
            if volume_logic.layer == VolumeLayer.PRIMARY or self._is_active_volume(volume_logic._id):
                logger.info(f"Volume {volume_logic._id} cannot be switched to secondary volume.")
                return
            self._reload_as_secondary_volume(volume_logic)
        else:
            if volume_logic.layer == VolumeLayer.SECONDARY:
                logger.info(f"Volume {volume_logic._id} cannot be switched to primary volume.")
                return
            self._reload_as_primary_volume(volume_logic)

    def set_object_visibility(self, volume_logic: VolumeObjectLogic, visible: bool) -> None:
        if self._is_primary_volume(volume_logic._id) and not self._is_active_volume(volume_logic._id) and visible:
            self._reload_as_primary_volume(volume_logic)
        else:
            self._display_handler.update_visibility(volume_logic, visible)
