import logging
from typing import Any

from trame.widgets.gwc import GirderProvider
from trame_server import Server
from undo_stack import Signal

from ...ui import GirderConnectionState, GirderConnectionUI
from ...utils import GirderConfig, is_valid_url
from ..base_logic import BaseLogic

logger = logging.getLogger(__name__)


class GirderConnectionLogic(BaseLogic[GirderConnectionState]):
    girder_connected = Signal(GirderConfig | None)
    user_connected = Signal(dict[str, Any] | None, str | None)

    def __init__(self, server: Server, girder_configs: dict[str, GirderConfig], default_url: str | None) -> None:
        super().__init__(server, GirderConnectionState)
        self.provider = GirderProvider(
            trame_server=self.server,
            api_root=(self.name.girder_api_root,),
            user_logged_in=(self._login, "[$event.user, $event.token]"),
            fetch_user=(self._login, "[$event.user, $event.token]"),
        )

        self._girder_configs = girder_configs
        self._girder_config = GirderConfig()
        self._init_girder(default_url)

        self.bind_changes(
            {
                (self.name.girder_api_root,): self._on_girder_api_root_changed,
                (self.name.girder_url,): self._on_girder_url_changed,
            }
        )

    def set_ui(self, connection_ui: GirderConnectionUI) -> None:
        connection_ui.log_out_clicked.connect(self._logout)

    def _init_girder(self, girder_url) -> None:
        self.data.girder_url = girder_url
        self._load_girder()

    def _load_girder(self) -> None:
        if self.data.girder_url:
            girder_config: GirderConfig = self._girder_configs.get(
                self.data.girder_url.strip("/"), GirderConfig(url=self.data.girder_url)
            )
            valid_url, self.data.girder_url_error = is_valid_url(girder_config.api_url)
            if valid_url:
                self.data.girder_api_root = girder_config.api_url
                self._girder_config = girder_config

    def _connect_girder(self, girder_api_root: str | None) -> None:
        self.provider.connect(girder_api_root)
        self.girder_connected(self._girder_config)

    def _disconnect_girder(self) -> None:
        self._logout()
        self.provider.disconnect()
        self._girder_config = GirderConfig()
        self.girder_connected(None)

    def _on_girder_api_root_changed(self, api_root: str | None) -> None:
        if api_root is None:
            self._disconnect_girder()
        else:
            self._connect_girder(api_root)

    def _on_girder_url_changed(self, girder_url: str | None) -> None:
        self.data.girder_api_root = None

        if girder_url:
            self._load_girder()
        else:
            self.data.girder_url_error = "URL required"

    def _login(self, info: dict[str, Any] | None, token: str | None) -> None:
        if info is not None and token is not None:
            self.data.girder_user_name = f"{info.get('firstName', None)} {info.get('lastName', None)}"
            self.user_connected(info, token)
            self.data.is_login_dialog_visible = False

    def _logout(self) -> None:
        if self.data.girder_user_name:
            self.provider.logout()
            self.data.girder_user_name = None
            self.user_connected(None, None)
