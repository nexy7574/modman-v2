import logging
import pathlib
import shutil
from concurrent.futures import ThreadPoolExecutor

import appdirs
import hashlib

import httpx
import rich
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TaskID,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from .modrinth import ModrinthAPI
from .models.modrinth import *


class ModManRuntime:
    def __init__(self, config: dict):
        self.log = logging.getLogger("modman.runtime")
        self.config = config
        self.config.setdefault("modman", {})
        self.modrinth = ModrinthAPI()
        self.cache_dir = pathlib.Path(appdirs.user_cache_dir("modman"))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.console = rich.get_console()

    @property
    def base_url(self) -> str:
        """The base URL for the modrinth API."""
        u = self.config["modman"].get("base_url", "https://api.modrinth.com/v2")
        if u.endswith("/"):
            return u[:-1]
        return u

    def _get_cached_file(self, file: VersionFile) -> pathlib.Path | None:
        f = self.cache_dir / file.filename
        if f.exists():
            return f.resolve()

    @staticmethod
    def _verify_file(path: pathlib.Path, method: str = "sha1", expected: str = None) -> bool:
        hasher = hashlib.new(method)
        with open(path, "rb") as f:
            while chunk := f.read(4096):
                hasher.update(chunk)
        return hasher.hexdigest() == expected

    def _download_file(self, task_id: TaskID, progress: Progress, client: httpx.Client, file: VersionFile):
        # noinspection PyArgumentList
        with client.stream("GET", str(file.url)) as response:
            response.raise_for_status()
            total = int(response.headers.get("Content-Length", 1))
            progress.update(task_id, total=total)
            with open(self.cache_dir / file.filename, "wb") as f:
                for chunk in response.iter_bytes(128000):
                    f.write(chunk)
                    progress.update(task_id, advance=len(chunk))

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
        locations: dict[VersionFile, pathlib.Path] = {}
        downloads: dict[VersionFile, pathlib.Path | None] = {}
        for file in files:
            downloads[file] = None
            self.log.debug("Checking if %r is already cached", file)
            cached_file = self._get_cached_file(file)
            if cached_file:
                self.log.info("Verifying file %r", cached_file)
                with self.console.status("Verifying file %r" % file.filename):
                    if not self._verify_file(cached_file, expected=file.hashes.sha1):
                        raise RuntimeError("File integrity check failed for %r" % file.filename)
                    else:
                        self.log.info("File %r verified", file.filename)
                        downloads[file] = cached_file
            else:
                self.log.info("%r is not downloaded. Will download.")

        with Progress(
                TextColumn("[bold blue]{task.fields[filename]}", justify="right"),
                BarColumn(bar_width=None),
                "[progress.percentage]{task.percentage:>3.1f}%",
                "•",
                DownloadColumn(),
                "•",
                TransferSpeedColumn(),
                "•",
                TimeRemainingColumn(),
        ) as progress:
            with httpx.Client(
                headers={"User-Agent": ModrinthAPI.USER_AGENT}
            ) as client:
                with ThreadPoolExecutor(self.config["modman"].get("concurrent_downloads", 3)) as executor:
                    tasks = {}
                    for file in files:
                        if downloads[file]:
                            continue
                        task_id = progress.add_task(file.filename, filename=file.filename)
                        tasks[task_id] = executor.submit(
                            self._download_file,
                            task_id,
                            progress,
                            client,
                            file,
                        )

                    for task_id, future in tasks.items():
                        future.result()
                        downloads[files[task_id]] = self.cache_dir / files[task_id].filename

        with self.console.status("Verifying & moving downloads...") as status:
            for file, cached_file in downloads.items():
                if not cached_file:
                    logging.warning("File %r was not downloaded", file.filename)
                    continue
                status.update("Verifying file %r" % file.filename)
                if not self._verify_file(cached_file, expected=file.hashes.sha1):
                    raise RuntimeError("File integrity check failed for %r" % file.filename)
                else:
                    self.log.info("File %r verified", file.filename)
                    status.update("Moving file %r" % file.filename)
                    locations[file] = shutil.move(cached_file, destination / file.filename)
        return locations
