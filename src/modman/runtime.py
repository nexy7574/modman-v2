import logging
import pathlib

import rich
from .modrinth import ModrinthAPI
from .models.modrinth import *


class ModManRuntime:
    def __init__(self, config: dict):
        self.log = logging.getLogger("modman.runtime")
        self.config = config
        self.modrinth = ModrinthAPI()

    def download_files(
            self,
            files: list[VersionFile],
            destination: pathlib.Path,
    ) -> dict[VersionFile, pathlib.Path]:
        """Downloads the given files to a cache, verifies, and then moves them.

        Any files found in the cache will be re-checked, and the download will be skipped.
        If any integrity checks fail, RuntimeError will be raised.

        :param files: The list of files to download.
        :param destination: The directory to move the files to.
        :return: A dictionary of VersionFile -> Path pairs.
        """
