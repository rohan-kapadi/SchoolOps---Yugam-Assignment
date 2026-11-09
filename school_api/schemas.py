from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class Parent(BaseModel):
    name: str
    phone: str
    language: str


class Student(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    class_name: str = Field(alias="class")
    bus_route_id: str | None = Field(alias="busRouteId")
    bus_stop: str | None = Field(alias="busStop")
    home_area: str = Field(alias="homeArea")
    home_pin: str = Field(alias="homePin")
    parent: Parent


class BusStop(BaseModel):
    order: int
    area: str
    pin: str
    lat: float
    lon: float


class BusRoute(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    driver_name: str = Field(alias="driverName")
    pickup_start_time: str = Field(alias="pickupStartTime")
    stops: list[BusStop]


class Event(BaseModel):
    id: str
    title: str
    date: date
    start: str
    end: str
    location: str
    lat: float | None = None
    lon: float | None = None
    outdoor: bool
    classes: str | list[str]
    description: str


class AttendanceDay(BaseModel):
    date: date
    absent: list[str]
    late: list[str]


class Timings(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    start: str
    end: str
    bus_pickup_start: str = Field(alias="busPickupStart")


class School(BaseModel):
    id: str
    name: str
    city: str
    state: str
    address: str
    lat: float
    lon: float
    timezone: str
    timings: Timings


class PolicyResponse(BaseModel):
    policy: str


class SchoolFile(BaseModel):
    """Shape of school-data.json. Extra keys such as _note are ignored."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    school: School
    policy: str
    classes: list[str]
    routes: list[BusRoute] = Field(alias="busRoutes")
    students: list[Student]
    events: list[Event]
    attendance: list[AttendanceDay]
