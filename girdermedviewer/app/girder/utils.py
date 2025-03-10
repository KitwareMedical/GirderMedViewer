from asyncio import to_thread
from contextlib import asynccontextmanager
from datetime import datetime
from enum import Enum
import logging
import os
import sys
from tempfile import TemporaryDirectory

logging.basicConfig(stream=sys.stdout)

logger = logging.getLogger(__name__)


def are_same_paths(path1, path2):
    return (os.path.normcase(os.path.realpath(os.path.abspath(path1))) ==
            os.path.normcase(os.path.realpath(os.path.abspath(path2))))


def format_date(date_str, format):
    return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%f+00:00").strftime(format)


class CacheMode(Enum):
    No = "No"
    Session = "Session"
    Permanent = "Permanent"


class FileFetcher:
    def __init__(self, girder_client, assetstore_dir=None, temp_dir=None, cache_mode=CacheMode.No):
        """
        :example:
        ```
        girder_client = GirderClient(apiUrl="http://localhost:8080/api/v1")
        girder_client.authenticate(apiKey="my_key")
        fetcher = FileFetcher(girder_client, cache_mode=CacheMode.Session)
        with fetcher.fetch_file(file) as file_path:
            ...
        ```
        """
        self.assetstore_dir_path = assetstore_dir
        self.girder_client = girder_client
        self.cache = cache_mode

        if cache_mode == CacheMode.Permanent:
            if temp_dir is None:
                raise Exception("A directory must be provided if cache mode is Permanent")
            if not os.path.exists(temp_dir):
                os.mkdir(temp_dir)
            self.temporary_directory = None
            self.temp_dir_path = temp_dir

        else:
            self.temporary_directory = TemporaryDirectory(dir=temp_dir)
            self.temp_dir_path = self.temporary_directory.name

        if (
            self.assetstore_dir_path is not None and
            are_same_paths(self.assetstore_dir_path, self.temp_dir_path)
        ):
            raise Exception("The temporary directory cannot match the assetstore directory.")

    def __del__(self):
        if self.cache == CacheMode.Session:
            self.clear_cache()

    def _download_file(self, file, file_path):
        logger.info(f"Download {file['name']} to {file_path}")
        self.girder_client.downloadFile(
            file["_id"],
            file_path
        )

    def get_item_files(self, item):
        return self.girder_client.listFile(item["_id"])

    def get_item_inherited_metadata(self, item):
        parent_folder = self.girder_client.getFolder(item["folderId"])
        metadata = parent_folder["meta"]
        # Fetch metadata of all parents
        while parent_folder["parentId"] != item["baseParentId"]:
            parent_folder = self.girder_client.getFolder(parent_folder["parentId"])
            metadata.update(parent_folder["meta"])
        return metadata

    @asynccontextmanager
    async def fetch_file(self, file):
        """
        First check if `file` does not already exist in assetstore.
        Then check if it does not already exist in cache.
        Finally download it if needed
        """
        file_path = None
        if self.assetstore_dir_path is not None:
            if "path" not in file:
                raise Exception("The Girder file is missing 'path' information. Make sure to use the girdermedviewer-plugin")
            file_path = os.path.join(self.assetstore_dir_path, file['path'])
            if not os.path.exists(file_path):
                logger.warning(f"The file {file_path} cannot be read from the assetstore, it will be downloaded instead")
                file_path = None

        if file_path is None:
            file_path = os.path.join(self.temp_dir_path, file['_id'], file["name"])
            if not os.path.exists(file_path):
                await to_thread(self._download_file, file, file_path)

        try:
            yield file_path
        finally:
            if self.cache == CacheMode.No:
                self.clear_cache(file_path)

    def clear_cache(self, file_path=None):
        if (
            file_path is not None and
            are_same_paths(os.path.dirname(file_path), self.temp_dir_path)
        ):
            if os.path.exists(file_path):
                os.remove(file_path)
        elif self.temporary_directory is not None:
            self.temporary_directory.cleanup()
