import asyncio
import logging
import traceback
from time import time
from typing import Any

from girder_client import GirderClient
from trame_server import Server
from trame_server.utils.asynchronous import create_task
from undo_stack import Signal

from ...ui import GirderBrowserState, GirderBrowserUI, GirderItemsUI
from ...utils import CacheMode, FileFetcher, GirderConfig, format_date
from ..base_logic import BaseLogic

logger = logging.getLogger(__name__)


class GirderBrowserLogic(BaseLogic[GirderBrowserState]):
    item_loaded = Signal(str, str)
    item_unselected = Signal(str)
    item_setting_changed = Signal(str, Any, str)

    def __init__(
        self,
        server: Server,
        girder_config: GirderConfig,
        cache_mode: str | None,
        temp_directory: str | None,
        date_format: str | None,
    ) -> None:
        super().__init__(server, GirderBrowserState)

        self._girder_config = girder_config
        self._date_format = date_format
        self._last_clicked = 0
        self._cache_mode = CacheMode(cache_mode) if cache_mode else CacheMode.No
        self._temp_directory = temp_directory

        # TODO: typed-state this
        self.state.selected = {}
        self.state.clean("selected")
        self.state.change("selected")(self._update_selected_in_location)

        self.update_girder_config(girder_config)

        self.tasks = {}

    def set_ui(self, browser_ui: GirderBrowserUI, items_ui: GirderItemsUI) -> None:
        browser_ui.row_clicked.connect(self._click_item)
        browser_ui.location_updated.connect(self._update_location)
        items_ui.item_deleted.connect(self._unselect_item)
        items_ui.download_canceled.connect(self._cancel_load_task)
        items_ui.setting_changed.connect(self.item_setting_changed)

    def _unselect_item(self, item) -> None:
        self.state.selected.pop(item["_id"])
        self.state.dirty("selected")
        self.item_unselected(item["_id"])

    def _unselect_items(self) -> None:
        while len(self.state.selected.values()) > 0:
            self._unselect_item(next(iter(self.state.selected.values())))

    def _select_item(self, item) -> None:
        assert item.get("_modelType") == "item", "Only item can be selected"
        item["humanCreated"] = format_date(item["created"], self._date_format)
        item["humanUpdated"] = format_date(item["updated"], self._date_format)
        item["parentMeta"] = self.file_fetcher.get_item_inherited_metadata(item)
        item["loading"] = False
        item["window"] = 0

        self.state.selected[item["_id"]] = item
        self.state.dirty("selected")

        self._create_load_task(item)

    def _click_item(self, item: dict[str, Any]) -> None:
        if item.get("_modelType") != "item":
            return
        # Ignore double click on item
        clicked_time = time()
        if clicked_time - self._last_clicked < 1:
            return
        self._last_clicked = clicked_time
        is_selected = item["_id"] in self.state.selected
        logger.debug(f"Toggle item {item} selected={is_selected}")
        if not is_selected:
            self._select_item(item)

    async def _load_item(self, item) -> None:
        logger.debug(f"Loading item {item}")
        try:
            files = list(self.file_fetcher.get_item_files(item))
            logger.debug(f"Files to load: {files}")
            if len(files) != 1:
                raise Exception(
                    "No file to load. Please check the selected item."
                    if (not files)
                    else "You are trying to load more than one file. \
                    If so, please load a compressed archive."
                )
            async with self.file_fetcher.fetch_file(files[0]) as file_path:
                self.item_loaded(str(file_path), item["_id"])
        except Exception:
            logger.error(f"Error loading file {item['_id']}: {traceback.format_exc()}")
            self._unselect_item(item)

    def _create_load_task(self, item) -> None:
        logger.debug(f"Creating load task for {item}")
        item["loading"] = True
        self.state.dirty("selected")
        self.state.flush()

        async def _load():
            await asyncio.sleep(1)
            try:
                await self._load_item(item)
            finally:
                item["loading"] = False
                self.state.dirty("selected")
                self.state.flush()
                self.tasks.pop(item["_id"], None)

        self.tasks[item["_id"]] = create_task(_load())

    def _cancel_load_task(self, item) -> None:
        logger.debug(f"Cancelling load task for {item}")
        task = self.tasks.get(item["_id"])
        if task and not task.done():
            task.cancel()
            self.tasks.pop(item["_id"], None)
            self._unselect_item(item)
            logger.info(f"Cancelled task for {item}")

    def update_girder_config(self, girder_config: GirderConfig) -> None:
        logger.debug(f"Setting api URL to {girder_config.api_url}")
        self._girder_config = girder_config
        self.file_fetcher = FileFetcher(
            GirderClient(apiUrl=girder_config.api_url), girder_config.assetstore, self._temp_directory, self._cache_mode
        )

    def _update_location(self, location: dict[str, Any] | None) -> None:
        if location is None:
            self.data.location = None

        location_id = location.get("_id")
        location_type = location.get("_modelType")
        if location_id and location_type:
            logger.debug(f"Location changed to {location}")
            self._typed_state.data.location = {"_id": location_id, "_modelType": location_type}
            self._update_selected_in_location(self.state.selected)

    def _update_selected_in_location(self, selected: dict[str, dict[str, Any]], **_kwargs) -> None:
        logger.debug(f"Selected changed to {selected}")
        location_id = self.data.location.get("_id") if self.data.location else None
        self.data.selected_in_location = [
            {"_id": item.get("_id")} for item in selected.values() if item["folderId"] == location_id
        ]

    def update_girder_user(self, user, token) -> None:
        logger.debug(f"Setting user to {user}")
        if user:
            if self.data.location is None:
                self._update_location(self._girder_config.default_location or user)
            self.data.is_browser_dialog_visible = True
        else:
            self._unselect_items()
            self._update_location(self._girder_config.default_location or user)

        self.file_fetcher.girder_client.setToken(token)
