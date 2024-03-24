import json
import math
import textwrap
import time
import typing

import httpx
import importlib.metadata
import logging

import rich
from rich.progress import Progress
from .models.modrinth import *


try:
    _version = importlib.metadata.version("modman")
except importlib.metadata.PackageNotFoundError:
    _version = "0.1.dev1"


class ModrinthAPI:
    USER_AGENT = f"modman/{_version} (https://github.com/nexy7574/modman-v2)"

    def __init__(
            self,
            client: httpx.Client = None,
            *,
            base_url: str = "https://api.modrinth.com/v2",
    ):
        self.log = logging.getLogger("modman.api.modrinth")
        if not client:
            self.http = httpx.Client(
                headers={"User-Agent": self.USER_AGENT},
                follow_redirects=True,
                max_redirects=5,
                base_url=base_url,
            )
            self.__cleanup_client = True
        else:
            self.http = client
            self.__cleanup_client = False

        self.ratelimit_reset = 0
        self.ratelimit_remaining = 500

    def __del__(self):
        if self.__cleanup_client:
            self.log.debug("Disposing of internal client.")
            self.http.close()

    def _get(self, url: str, params: dict[str, typing.Any] = None) -> dict | list:
        if self.ratelimit_remaining == 0:
            self.log.warning("Ratelimit reached, waiting %s seconds", self.ratelimit_reset)
            with Progress() as progress:
                now = time.time()
                wait_seconds = math.ceil(self.ratelimit_reset - now)
                task = progress.add_task("Waiting for rate-limit.", total=wait_seconds)
                for i in range(wait_seconds):
                    time.sleep(1)
                    progress.update(task, advance=1)
        self.log.debug(
            "Ratelimit has %d hits left, resets in %d seconds",
            self.ratelimit_remaining,
            self.ratelimit_reset
        )
        with rich.get_console().status("[cyan dim]GET " + url):
            for i in range(5):
                try:
                    response = self.http.get(url, params=params)
                except httpx.ConnectError:
                    self.log.warning("Connection error, retrying...")
                    continue
                break
            else:
                raise RuntimeError("Failed to connect to Modrinth API")
        self.ratelimit_reset = int(response.headers.get("x-ratelimit-reset", 0))
        self.ratelimit_remaining = int(response.headers.get("x-ratelimit-remaining", 100))
        if response.status_code == 429:
            self.log.warning("Request was rate-limited, re-calling.")
            return self._get(url, params)
        self.log.debug(textwrap.shorten(response.text, 10240))
        if response.status_code not in range(200, 300):
            response.raise_for_status()
        return response.json()

    def search(
            self,
            query: str,
            limit: int = 100,
            offset: int = 0,
            index: SearchIndexEnum = SearchIndexEnum.RELEVANCE,
    ) -> ProjectSearchResultPage:
        """
        Searches modrinth with the given parameters to find projects.

        :param query: The main search query
        :param limit: The maximum number of results to return (between 0 and 100)
        :param offset: The number of results to skip
        :param index: In what way to filter the results.
        :return:
        """

    def fetch_projects(
            self,
            *identifiers: str
    ) -> list[Project]:
        """
        Fetches a list of projects from Modrinth. Unknown ones are simply omitted.

        :param identifiers: An iterable of names, IDs, or slugs.
        :return: a list of found projects.
        """
        if not identifiers:
            return []
        projects = []

        response = self._get("/projects", params={"ids": json.dumps(identifiers)})
        for project in response:
            try:
                parsed = Project(**project)
            except Exception as e:
                self.log.warning("Failed to parse project: %s", e)
                continue
            projects.append(parsed)

        return projects

    def fetch_project(
            self,
            identifier: str
    ) -> Project | None:
        """
        Fetches just one project from Modrinth, returning None if it was not found.

        :param identifier: The project's name, ID, or slug.
        :return: The project, if available.
        """
        try:
            return self.fetch_projects(identifier).pop()
        except IndexError:
            return

    def fetch_versions(
            self,
            *identifiers: str
    ) -> list[Version]:
        """
        Fetches a list of versions from Modrinth. Unknown ones are simply omitted.

        :param identifiers: An iterable of names, IDs, or slugs.
        :return: a list of found versions.
        """
        if not identifiers:
            return []
        versions = []

        response = self._get("/versions", params={"ids": json.dumps(identifiers)})
        for version in response:
            try:
                parsed = Version(**version)
            except Exception as e:
                self.log.warning("Failed to parse version: %s", e)
                continue
            versions.append(parsed)

        return versions

    def fetch_version(self, identifier: str) -> Version | None:
        """
        Fetches just one version from Modrinth, returning None if it was not found.

        :param identifier: The version's name, ID, or slug.
        :return: The version, if available.
        """
        try:
            return self.fetch_versions(identifier).pop()
        except IndexError:
            return

    def fetch_project_versions(
            self,
            project: Project | str,
            loaders: list[str] | None = None,
            game_versions: list[str] | None = None,
            featured: bool | None = None,
    ) -> list[Version]:
        """
        Fetches all versions of a project from Modrinth.

        :param project: The project or project identifier to fetch versions for.
        :param loaders: A list of loaders to filter by.
        :param game_versions: A list of game versions to filter by.
        :param featured: Whether to only fetch featured versions.
        :return: A list of versions.
        """
        if not isinstance(project, str):
            project = project.id

        versions = []
        query = {}
        if loaders:
            query["loaders"] = json.dumps(loaders)
        if game_versions:
            query["game_versions"] = json.dumps(game_versions)
        if featured is not None:
            query["featured"] = json.dumps(featured)

        response = self._get(f"/project/{project}/version", params=query)
        for version in response:
            try:
                parsed = Version(**version)
            except Exception as e:
                self.log.warning("Failed to parse version: %s", e)
                continue
            versions.append(parsed)

        return versions

    def fetch_version_from_file_hash(
            self,
            file_hash: str,
            *,
            algorithm: str = "sha512"
    ) -> Version | None:
        """
        Fetches the version of a project that has the given file hash.

        :param file_hash: The hash of the file to search for.
        :param algorithm: SHA1 or SHA512, defaults to SHA512.
        :return: The found version, if available.
        """
        response = self._get(f"/version_file/{file_hash}", params={"algorithm": algorithm})
        try:
            return Version(**response)
        except Exception as e:
            self.log.warning("Failed to parse version: %s", e)
            return

    @staticmethod
    def get_primary_file(*files: VersionFile) -> VersionFile:
        """
        Returns the primary file from a list of version files.

        :param files: The files to search through.
        :return: The primary file.
        """
        for file in files:
            if file.primary:
                return file
        return files[0]
