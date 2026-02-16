import logging
import sys
from configparser import ConfigParser
from pathlib import Path

from trame_server import Server

from ..ui import AppState, AppUI
from ..utils import AppConfig, GirderConfig
from .base_logic import BaseLogic
from .girder import GirderLogic
from .vtk.scene_logic import SceneLogic

logger = logging.getLogger(__name__)


class AppLogic(BaseLogic[AppState]):
    def __init__(self, server: Server) -> None:
        super().__init__(server, AppState)
        self._load_app_config()

        self._scene_logic = SceneLogic(self.server)
        self._girder_logic = GirderLogic(self.server, self._scene_logic, self.app_config)
        self.provider = self._girder_logic.connection_logic.provider

        self._scene_logic.objects_changed.connect(self._on_scene_changed)

    def set_ui(self, ui: AppUI) -> None:
        self._girder_logic.set_ui(ui)
        self._scene_logic.set_views(ui.quad_view.views)

    def _load_app_config(self, config_file_path: Path | None = None) -> None:
        """
        Load the configuration file app.cfg if any and set the state variables accordingly.
        If provided, app.cfg must at least contain girder/api_root.
        """
        if config_file_path is None:
            current_working_directory = Path.cwd()
            config_file_path = current_working_directory / "app.cfg"

        if not config_file_path.exists():
            return

        config_parser = ConfigParser()
        config_parser.read(config_file_path)
        config_dict = {s: dict(config_parser.items(s)) for s in config_parser.sections()}

        app_config = {}
        app_config.update(config_dict.get("download", {}))
        app_config.update(config_dict.get("logging", {}))
        app_config.update(config_dict.get("girder", {}))
        app_config["girder_configs"] = {
            url: GirderConfig(url=url, **config) for url, config in config_dict.items() if url.startswith("http")
        }
        self.app_config = AppConfig(**app_config)

        logging.basicConfig(stream=sys.stdout)
        # Silence dependencies logs and keep only the application ones
        logging.getLogger().setLevel(logging.WARNING)
        logging.getLogger(__package__).setLevel(self.app_config.log_level)

    def _on_scene_changed(self, loaded_objects: list[str]):
        self.data.is_viewer_disabled = len(loaded_objects) == 0
