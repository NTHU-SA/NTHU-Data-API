"""Internal payload shapes for MCP tool helpers (not public tool schemas)."""

from typing import Literal, NotRequired, TypedDict


class LocationResult(TypedDict):
    name: str
    latitude: str
    longitude: str


class CampusPersonResult(TypedDict):
    name: str
    title: NotRequired[str | None]
    extension: NotRequired[str | None]
    email: NotRequired[str | None]
    note: NotRequired[str | None]


class CampusDepartmentDetailsResult(TypedDict):
    contact: NotRequired[dict[str, object]]
    departments: NotRequired[list[dict[str, object]]]
    people: NotRequired[list[CampusPersonResult]]


class CampusDepartmentResult(TypedDict):
    index: str
    name: str
    parent_name: NotRequired[str | None]
    url: NotRequired[str | None]
    details: NotRequired[CampusDepartmentDetailsResult]


class CampusResult(TypedDict):
    locations: list[LocationResult]
    departments: list[CampusDepartmentResult]
    people: list[CampusPersonResult]


class BusDepartureResult(TypedDict):
    time: str
    description: str
    dep_stop: str
    line: str
    bus_type: str


class BusArrivalResult(TypedDict):
    stop: str
    arrive_time: str


class BusDetailedResult(TypedDict):
    dep_info: BusDepartureResult
    stops_time: list[BusArrivalResult]


class BusStopResult(TypedDict):
    name: str
    name_en: str
    latitude: str
    longitude: str


class BusRouteInfoResult(TypedDict, total=False):
    direction: str
    duration: str
    route: str
    routeEN: str


class BusResult(TypedDict):
    current_time: str
    day_type: str
    buses: list[BusDepartureResult | BusDetailedResult]
    route_info: list[BusRouteInfoResult]
    stop_name: NotRequired[str]
    stop_info: NotRequired[list[BusStopResult]]


class CoursesResult(TypedDict):
    count: int
    courses: list[dict[str, object]]


class AnnouncementArticleResult(TypedDict):
    title: str | None
    link: str | None
    date: str | None


class AnnouncementSourceResult(TypedDict):
    department: str | None
    language: str | None
    articles: list[AnnouncementArticleResult]


class AnnouncementsResult(TypedDict):
    count: int
    sources: list[AnnouncementSourceResult]


class DiningRestaurantResult(TypedDict):
    name: str | None
    phone: str | None
    schedule: dict[str, object] | None
    note: str | None


class DiningBuildingResult(TypedDict):
    building: str | None
    restaurants: list[DiningRestaurantResult]


class DiningBuildingsResult(TypedDict):
    buildings: list[DiningBuildingResult]


class OpenRestaurantResult(TypedDict):
    name: str | None
    area: str | None
    phone: str | None
    schedule: dict[str, object] | None


class OpenDiningResult(TypedDict):
    schedule: Literal["today", "weekday", "saturday", "sunday"]
    open_restaurants: list[OpenRestaurantResult]


class LibrarySpaceResult(TypedDict):
    zone: str | None
    type: str | None
    available: str | int | None


class LibrarySpacesResult(TypedDict):
    spaces: list[LibrarySpaceResult]


class LibraryItemsResult(TypedDict):
    items: list[dict[str, str]]


class NewsletterArticleResult(TypedDict):
    title: str | None
    date: str | None


class NewsletterResult(TypedDict):
    name: str | None
    link: str | None
    latest_articles: list[NewsletterArticleResult]


class NewslettersResult(TypedDict):
    count: int
    newsletters: list[NewsletterResult]


class EnergyZoneResult(TypedDict):
    name: str | None
    usage_kw: float
    capacity_kw: float | None
    usage_percent: float
    last_updated: str | None


class EnergyResult(TypedDict):
    zones: list[EnergyZoneResult]
