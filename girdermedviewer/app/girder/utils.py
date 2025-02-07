import os
import sys
from contextlib import contextmanager
from enum import Enum
from tempfile import TemporaryDirectory

import logging
logging.basicConfig(stream=sys.stdout)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


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
        if not self.temp_dir_path:
            if cache_mode == CacheMode.Permanent:
                raise Exception("A directory must be provided if cache mode is Permanent")
            self.temporary_directory = TemporaryDirectory()
            self.temp_dir_path = self.temporary_directory.name
        self.girder_client = girder_client
        self.cache = cache_mode

    def __del__(self):
        if self.cache == CacheMode.Session:
            self.clear_cache()

    def get_item_files(self, item):
        return self.girder_client.listFile(item["_id"])

    @contextmanager
    def fetch_file(self, file):
        fetched_from_assetstore = False
        if self.assetstore_dir_path:
            if "path" not in file:
                logger.info("The file path in assetstore is unknown. Make sure to use the girdermedviewer-plugin")
            file_path = os.path.join(self.assetstore_dir_path, file['path'])
            if os.path.exists(file_path):
                fetched_from_assetstore = True
            else:
                logger.info("The file cannot be read from the assetstore, it will be downloaded instead")

        if not fetched_from_assetstore:
            file_path = os.path.join(self.temp_dir_path, file['_id'], file["name"])
            if not os.path.exists(file_path):
                logger.debug(f"Downloading {file_path}")
                self.girder_client.downloadFile(
                    file["_id"],
                    file_path
                )
                logger.debug(f"Downloaded {file_path}")
        try:
            yield file_path
        finally:
            if not fetched_from_assetstore and self.cache == CacheMode.No:
                self.clear_cache(file)

    def clear_cache(self, file=None):
        if file is not None:
            file_path = os.path.join(self.temp_dir_path, file['_id'], file["name"])
            os.remove(file_path)
        else:
            self.temp_dir_path.cleanup()
