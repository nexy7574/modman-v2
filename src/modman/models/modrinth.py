import datetime
import enum
import typing
from pydantic import BaseModel, Field, AnyUrl


__all__ = (
    "SearchIndexEnum",
    "CLIENT_SIDE",
    "SERVER_SIDE",
    "STATUS",
    "REQUESTED_STATUS",
    "PROJECT_TYPE",
    "MONETIZATION_STATUS",
    "DEPENDENCY_TYPE",
    "VERSION_TYPE",
    "VERSION_STATUS",
    "VERSION_REQUESTED_STATUS",
    "DonationObject",
    "LicenseObject",
    "Project",
    "ProjectSearchResultPage",
    "VersionDependency",
    "VersionFileHashes",
    "VersionFile",
    "Version",
    "AllProjectDependencies",
)


class SearchIndexEnum(enum.Enum):
    RELEVANCE = "relevance"
    DOWNLOADS = "downloads"
    FOLLOWS = "follows"
    NEWEST = "newest"
    UPDATED = "updated"


CLIENT_SIDE = SERVER_SIDE = typing.Literal["required", "optional", "unsupported"]
STATUS = typing.Literal[
    "approved",
    "archived",
    "rejected",
    "draft",
    "unlisted",
    "processing",
    "withheld",
    "scheduled",
    "private",
    "unknown"
]
REQUESTED_STATUS = typing.Literal[
    "approved", "archived", "unlisted", "private", "draft"
]
PROJECT_TYPE = typing.Literal["mod", "modpack", "resourcepack", "shader"]
MONETIZATION_STATUS = typing.Literal[
    "monetized", "demonetized", "force-demonetized"
]
DEPENDENCY_TYPE = typing.Literal["required", "optional", "incompatible", "embedded"]
VERSION_TYPE = typing.Literal["release", "beta", "alpha"]
VERSION_STATUS = typing.Literal[
    "listed",
    "archived",
    "draft",
    "unlisted",
    "scheduled",
    "unknown"
]
VERSION_REQUESTED_STATUS = typing.Literal[
    "listed",
    "archived",
    "draft",
    "unlisted"
]


class DonationObject(BaseModel):
    """Represents a donation URL for a project."""
    url: AnyUrl = Field(description="The URL to the donation page")
    platform: str = Field(description="The platform that the donation page is on")
    id: str = Field(description="The ID of the donation platform")


class LicenseObject(BaseModel):
    """Represents a license for a project."""
    name: str = Field(description="The name of the license")
    url: AnyUrl | None = Field(
        None,
        description="The URL to the license text or information"
    )
    id: str = Field(description="The SPDX license ID of a project")


class Project(BaseModel):
    """Represents a project hosted on Modrinth."""
    slug: str = Field(
        description="The slug or vanity URL of the project",
        pattern=r"^[\w!@$()`.+,\"\-']{3,64}$",
        min_length=3,
        max_length=64,
    )
    title: str = Field(description="The title or name of the project")
    description: str = Field(description="A short description of the project")
    categories: list[str] = Field(description="A list of the categories that the project has")
    client_side: CLIENT_SIDE = Field(description="The client side support of the project")
    server_side: SERVER_SIDE = Field(description="The server side support of the project")
    body: str = Field(description="The full description of the project")
    status: STATUS = Field(description="The status of the project")
    requested_status: REQUESTED_STATUS | None = Field(
        None,
        description="The requested status when submitting for review or scheduling the project for release"
    )
    additional_categories: list[str] = Field(
        [],
        description="A list of non-primary additional categories"
    )
    issues_url: AnyUrl | None = Field(
        None,
        description="The URL to the issue tracker of the project"
    )
    source_url: AnyUrl | None = Field(
        None,
        description="The URL to the source code of the project"
    )
    wiki_url: AnyUrl | None = Field(
        None,
        description="The URL to the wiki or documentation of the project"
    )
    discord_url: AnyUrl | None = Field(
        None,
        description="The URL to the Discord server of the project"
    )
    donation_urls: list[DonationObject] = Field(
        [],
        description="A list of donation URLs for the project"
    )
    project_type: PROJECT_TYPE = Field(description="The type of project")
    downloads: int = Field(description="The number of downloads the project has")
    icon_url: AnyUrl | None = Field(None, description="The URL to the icon of the project")
    color: int | None = Field(None, description="The RGB color of the project")
    thread_id: str | None = Field(
        None,
        description="The ID of the moderation thread associated with this project"
    )
    monetization_status: MONETIZATION_STATUS | None = Field(
        None,
        description="The monetization status of the project"
    )
    id: str = Field(description="The ID of the project, encoded in base62")
    team: str = Field(description="The team that owns the project")
    published: datetime.datetime = Field(description="The date and time the project was published")
    updated: datetime.datetime = Field(description="The date and time the project was last updated")
    approved: datetime.datetime | None = Field(
        None,
        description="The date and time the project was approved"
    )
    queued: datetime.datetime | None = Field(
        None,
        description="The date and time the project was queued for approval"
    )
    followers: int = Field(description="The number of followers the project has")
    license: LicenseObject = Field(description="The license of the project")
    versions: list[str] = Field(description="A list of the version IDs of the project")
    game_versions: list[str] = Field(description="A list of the game versions the project supports")

    def related(self, target: str) -> bool:
        """Checks that <identifier> relates to this project"""
        if target.strip().lower() == self.id.strip().lower():
            return True
        if target.strip().casefold() == self.title.strip().casefold():
            return True
        if target.strip().casefold() == self.slug.strip().casefold():
            return True
        return False


class ProjectSearchResultPage(BaseModel):
    """Represents a page of results from /search."""
    hits: list[Project] = Field(description="The results")
    offset: int = Field(description="The number of results that were skipped by the query")
    limit: int = Field(description="The number of results that were returned by the query")
    total_hits: int = Field(description="The total number of results that match the query")


class VersionDependency(BaseModel):
    """Represents a dependency of a version."""
    version_id: str | None = Field(None, description="The ID of the version that this version depends on")
    project_id: str | None = Field(None, description="The ID of the project that this version depends on")
    file_name: str | None = Field(
        None,
        description="The file name of the dependency, mostly used for showing external dependencies on modpacks"
    )
    dependency_type: DEPENDENCY_TYPE = Field(description="The type of dependency")


class VersionFileHashes(BaseModel):
    """Represents the hashes of a version file."""
    sha1: str | None = Field(None, description="The SHA1 hash of the file")
    sha256: str | None = Field(None, description="The SHA256 hash of the file")


class VersionFile(BaseModel):
    hashes: VersionFileHashes = Field(description="The hashes of the file")
    url: AnyUrl = Field(description="The URL to the file")
    filename: str = Field(description="The name of the file")
    primary: bool = Field(description="Whether the file is the primary file of the version")
    size: int = Field(description="The size of the file in bytes")


class Version(BaseModel):
    """Represents a version of a project."""
    name: str = Field(description="The name of the version")
    version_number: str = Field(description="The version number. Ideally will follow semantic versioning")
    changelog: str | None = Field(None, description="The changelog for the version")
    dependencies: list[VersionDependency] = Field([], description="The dependencies of the version")
    game_versions: list[str] = Field(description="The game versions that the version supports")
    version_type: VERSION_TYPE = Field(description="The type of version")
    loaders: list[str] = Field(description="The loaders that the version supports")
    featured: bool = Field(description="Whether the version is featured")
    status: VERSION_STATUS = Field(description="The status of the version")
    requested_status: VERSION_REQUESTED_STATUS | None = Field(
        None,
        description="The requested status when submitting for review or scheduling the version for release"
    )
    id: str = Field(description="The ID of the version, encoded in base62")
    project_id: str = Field(description="The ID of the project that the version belongs to")
    author_id: str = Field(description="The ID of the author of the version")
    date_published: datetime.datetime
    downloads: int
    files: list[VersionFile] = Field(description="The files of the version")


class AllProjectDependencies(BaseModel):
    """Represents the result of /project/:id/dependencies."""
    projects: list[Project] = Field(description="The projects that the project depends on")
    versions: list[Version] = Field(description="The versions that the project depends on")
