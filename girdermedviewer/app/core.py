import logging
import sys

from trame.app import TrameApp
from trame_server import Server

from .widgets import AppLayout, AppLogic, AppUI


class MedViewerApp(TrameApp):
    def __init__(self, server: Server | None, **kwargs) -> None:
        super().__init__(server, **kwargs)
        self._layout = AppLayout(self.server)
        self._logic = AppLogic(self.server)
        self._ui = AppUI(self._layout, self._logic.provider, self._logic.app_config, self._logic.render_windows)

        logging.basicConfig(stream=sys.stdout)
        # Silence dependencies logs and keep only the application ones
        logging.getLogger().setLevel(logging.WARNING)
        logging.getLogger(__package__).setLevel(self._logic.app_config.log_level)

        self._logic.set_ui(self._ui)
