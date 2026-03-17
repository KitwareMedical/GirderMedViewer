import logging
from time import time
from typing import Any

from trame_server import Server
from undo_stack import Signal

from ...ui import GirderBrowserState, GirderBrowserUI
from ...utils import GirderItem
from ..base_logic import BaseLogic

logger = logging.getLogger(__name__)


class GirderBrowserLogic(BaseLogic[GirderBrowserState]):
    item_selected = Signal(Any)
    item_unselected = Signal(Any)

    def __init__(
        self,
        server: Server,
    ) -> None:
        super().__init__(server, GirderBrowserState)

        self._last_clicked = 0

        self.bind_changes({self.name.selected_items: self._update_selected_items_in_location})

        self.tasks = {}

    def set_ui(self, browser_ui: GirderBrowserUI) -> None:
        browser_ui.row_clicked.connect(self._click_item)
        browser_ui.location_updated.connect(self._update_location)

    def _is_item_selected(self, item_id: str) -> bool:
        return any(item_id == selected_item._id for selected_item in self.data.selected_items)

    def _select_item(self, item: dict[str, Any]):
        if self._is_item_selected(item["_id"]):
            logger.info(f"Item {item['_id']} is already selected")
            return

        logger.debug(f"Item {item['_id']} selected")
        self.data.selected_items += [GirderItem(_id=item["_id"], location_id=item["folderId"])]
        self.item_selected(item)

    def _click_item(self, item: dict[str, Any]) -> None:
        if item.get("_modelType") != "item":
            return

        # Ignore double click on item
        clicked_time = time()
        if clicked_time - self._last_clicked < 1:
            return
        self._last_clicked = clicked_time

        logger.debug(f"Item {item['_id']} clicked")
        self._select_item(item)

    def _update_location(self, location: dict[str, Any] | None) -> None:
        new_location = None
        if location is not None:
            location_id = location.get("_id")
            location_type = location.get("_modelType")
            if location_id and location_type:
                logger.debug(f"Location changed to {location_id}")
                new_location = {"_id": location_id, "_modelType": location_type}

        self.data.location = new_location
        self._update_selected_items_in_location(self.data.selected_items)

    def _update_selected_items_in_location(self, selected_items: list[GirderItem]) -> None:
        """Updates the elements selected in the current folder"""
        location_id = self.data.location.get("_id") if self.data.location else None
        self.data.selected_items_in_location = [
            selected_item for selected_item in selected_items if selected_item.location_id == location_id
        ]

    def unselect_item(self, _, item_id: str) -> None:
        if not self._is_item_selected(item_id):
            logger.info(f"Item {item_id} is not currently selected")
            return

        logger.debug(f"Item {item_id} unselected")
        self.data.selected_items = [
            selected_item for selected_item in self.data.selected_items if item_id != selected_item._id
        ]
        self.item_unselected(item_id)

    def update_girder_user(self, user: dict[str, Any] | None) -> None:
        logger.debug(f"Setting user to {user}")
        self._update_location(self.data.default_location or user)
        self.data.is_browser_dialog_visible = user is not None
        self.data.is_user_connected = user is not None

    def update_girder_default_location(self, default_location):
        self.data.default_location = default_location
        self._update_location(default_location)
