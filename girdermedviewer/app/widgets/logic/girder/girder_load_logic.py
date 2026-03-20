import asyncio
import logging
import traceback
from typing import Any

from girder_client import GirderClient, HttpError
from trame_server import Server
from trame_server.utils.asynchronous import create_task
from undo_stack import Signal

from ...utils import CacheMode, FileFetcher, FileFetchError, GirderConfig, format_date
from ..base_logic import BaseLogic
from ..scene import (
    SceneObject,
    SceneObjectInfo,
    SceneObjectMetadata,
)

logger = logging.getLogger(__name__)


class GirderLoadLogic(BaseLogic[None]):
    item_fetched = Signal(str, str)
    item_unfetched = Signal(str)
    item_formatted = Signal(SceneObject)
    item_unformatted = Signal(str)

    def __init__(
        self,
        server: Server,
        girder_config: GirderConfig,
        cache_mode: str | None,
        temp_directory: str | None,
        date_format: str | None,
    ) -> None:
        super().__init__(server, None)
        self._girder_config = girder_config
        self._date_format = date_format
        self._cache_mode = CacheMode(cache_mode) if cache_mode else CacheMode.No
        self._temp_directory = temp_directory

        self.update_girder_config(girder_config)

        self.fetch_tasks = {}

    def _create_scene_object_from_item(self, item: dict[str, Any]) -> SceneObject:
        parent_meta = self.file_fetcher.get_item_inherited_metadata(item).items()
        info = SceneObjectInfo(
            self.server,
            created=format_date(item.get("created"), self._date_format),
            updated=format_date(item.get("updated"), self._date_format),
            size=item.get("humanSize", "0 B"),
        )
        metadata = SceneObjectMetadata(
            self.server,
            parent_meta={str(key): str(value) for key, value in parent_meta},
            meta={str(key): str(value) for key, value in item.get("meta", {}).items()},
        )
        return SceneObject(
            self.server,
            name=item.get("name", ""),
            info=info,
            metadata=metadata,
            database_id=item.get("_id"),
        )

    async def _fetch_item(self, task_id: str, item: dict[str, Any]) -> None:
        logger.debug(f"Fetching item {item['_id']}")
        try:
            files = list(self.file_fetcher.get_item_files(item))
            logger.debug(f"Files to fetch: {files}")

            if len(files) != 1:
                raise FileFetchError("No file to fetch..." if not files else "Multiple files found...")

            async with self.file_fetcher.fetch_file(files[0]) as file_path:
                self.item_fetched(str(file_path), task_id)

        except (HttpError, FileFetchError):
            logger.error(f"Error fetching files for {item['_id']}: {traceback.format_exc()}")
            self.item_unfetched(task_id)

    def create_fetch_task(self, task_id: str, item: dict[str, Any]) -> None:
        logger.debug(f"Creating fetch task {task_id} for {item['_id']}")

        async def _fetch():
            await asyncio.sleep(1)
            try:
                await self._fetch_item(task_id, item)
            finally:
                self.fetch_tasks.pop(task_id, None)

        self.fetch_tasks[task_id] = create_task(_fetch())

    def cancel_fetch_task(self, task_id: str) -> None:
        logger.debug(f"Cancelling fetch task {task_id}")
        task = self.fetch_tasks.get(task_id)
        if task and not task.done():
            task.cancel()
            self.fetch_tasks.pop(task_id, None)

        self.item_unfetched(task_id)
        logger.debug(f"Cancelled fetch task {task_id}")

    def format_item(self, item: dict[str, Any]) -> None:
        try:
            scene_object = self._create_scene_object_from_item(item)
            self.item_formatted(scene_object)
            self.create_fetch_task(scene_object._id, item)
        except HttpError:
            logger.error(f"Error formatting info and metadata for {item['_id']}: {traceback.format_exc()}")
            self.item_unformatted(item["_id"])

    def update_girder_config(self, girder_config: GirderConfig) -> None:
        logger.debug(f"Setting api URL to {girder_config.api_url}")
        self._girder_config = girder_config
        self.file_fetcher = FileFetcher(
            GirderClient(apiUrl=girder_config.api_url), girder_config.assetstore, self._temp_directory, self._cache_mode
        )

    def update_token(self, token) -> None:
        logger.debug(f"Setting token to {token}")
        self.file_fetcher.girder_client.setToken(token)
