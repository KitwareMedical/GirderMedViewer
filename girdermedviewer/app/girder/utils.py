import os
from contextlib import contextmanager
from enum import Enum
from tempfile import TemporaryDirectory

import logging

logger = logging.getLogger(__name__)


def are_same_paths(path1, path2):
    return (os.path.normcase(os.path.realpath(os.path.abspath(path1))) ==
            os.path.normcase(os.path.realpath(os.path.abspath(path2))))


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
        self.temp_dir_path = temp_dir
        self.girder_client = girder_client
        self.cache = cache_mode

        if self.temp_dir_path is None:
            if cache_mode == CacheMode.Permanent:
                raise Exception("A directory must be provided if cache mode is Permanent")
            self.temporary_directory = TemporaryDirectory()
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

    @contextmanager
    def fetch_file(self, file):
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
                self._download_file(file, file_path)

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
        else:
            self.temp_dir_path.cleanup()
