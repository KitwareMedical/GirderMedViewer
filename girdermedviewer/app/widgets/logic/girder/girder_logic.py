import logging
from typing import Any

from trame_server import Server
from undo_stack import Signal

from ...ui import AppUI
from ...utils import AppConfig, GirderConfig
from ..base_logic import BaseLogic
from ..vtk.scene_logic import SceneLogic
from .girder_browser_logic import GirderBrowserLogic
from .girder_connection_logic import GirderConnectionLogic

logger = logging.getLogger(__name__)


class GirderLogic(BaseLogic[None]):
    girder_connected = Signal(bool)
    user_connected = Signal(bool)

    def __init__(self, server: Server, scene: SceneLogic, app_config: AppConfig) -> None:
        super().__init__(server, None)
        self._load_girder_config(app_config)

        self.connection_logic = GirderConnectionLogic(
            server, app_config.girder_configs, default_url=app_config.default_url
        )
        self.browser_logic = GirderBrowserLogic(
            server,
            self.config,
            app_config.cache_mode,
            app_config.temp_directory,
            app_config.date_format,
        )

        self.connection_logic.girder_connected.connect(self._update_config)
        self.connection_logic.user_connected.connect(self._update_user)
        self.browser_logic.item_loaded.connect(scene.add_scene_object)
        self.browser_logic.item_unselected.connect(scene.remove_scene_object)
        self.browser_logic.item_setting_changed.connect(scene.update_object_property)

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
        self.browser_logic.update_girder_config(self.config)
        self.girder_connected(self.config.url is not None)

    def _update_user(self, user: dict[str, Any] | None, token: str | None) -> None:
        self.browser_logic.update_girder_user(user, token if token else "")
        self.user_connected(user is not None)
