import logging
from typing import Any

from trame_server import Server
from undo_stack import Signal

from ...ui import AppUI
from ...utils import AppConfig, GirderConfig
from ..base_logic import BaseLogic
from ..scene import SceneLogic
from .girder_browser_logic import GirderBrowserLogic
from .girder_connection_logic import GirderConnectionLogic
from .girder_load_logic import GirderLoadLogic

logger = logging.getLogger(__name__)


class GirderLogic(BaseLogic[None]):
    girder_connected = Signal(bool)

    def __init__(self, server: Server, scene_logic: SceneLogic, app_config: AppConfig) -> None:
        super().__init__(server, None)
        self._load_girder_config(app_config)

        self.connection_logic = GirderConnectionLogic(
            server, app_config.girder_configs, default_url=app_config.default_url
        )
        self.browser_logic = GirderBrowserLogic(
            server,
        )
        self.load_logic = GirderLoadLogic(
            server,
            girder_config=self.config,
            cache_mode=app_config.cache_mode,
            temp_directory=app_config.temp_directory,
            date_format=app_config.date_format,
        )
        self.scene_logic = scene_logic

        self.connection_logic.girder_connected.connect(self._update_config)
        self.connection_logic.user_connected.connect(self._update_user)

        # Connect girder and scene logics
        self.browser_logic.item_selected.connect(self.load_logic.format_item)
        self.load_logic.item_formatted.connect(scene_logic.add_object)
        self.load_logic.item_unformatted.connect(self.browser_logic.unselect_item)
        self.load_logic.item_fetched.connect(scene_logic.add_file_object_to_views)
        self.load_logic.item_unfetched.connect(scene_logic.remove_object)

        scene_logic.object_load_canceled.connect(self.load_logic.cancel_fetch_task)
        scene_logic.object_removed.connect(self.browser_logic.unselect_item)

    def set_ui(self, ui: AppUI) -> None:
        self.connection_logic.set_ui(ui.girder_connection_ui)
        self.browser_logic.set_ui(ui.girder_browser_ui)

    def _load_girder_config(self, app_config: AppConfig) -> None:
        if app_config.default_url is not None:
            self.config = app_config.girder_configs.get(
                app_config.default_url,
                GirderConfig(app_config.default_url),
            )

    def _update_config(self, girder_config: GirderConfig | None) -> None:
        self.config = girder_config if girder_config else GirderConfig()
        self.browser_logic.update_girder_default_location(self.config.default_location)
        self.load_logic.update_girder_config(self.config)
        self.girder_connected(self.config.url is not None)

    def _update_user(self, user: dict[str, Any] | None, token: str | None) -> None:
        self.browser_logic.update_girder_user(user)
        self.load_logic.update_token(token)

        if user is None:
            self.scene_logic.clear_scene()
