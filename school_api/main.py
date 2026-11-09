from contextlib import asynccontextmanager

from fastapi import FastAPI

from school_api.data_loader import get_school_data
from school_api.routes import attendance, buses, events, policy, school, students


@asynccontextmanager
async def lifespan(_app: FastAPI):
    get_school_data()
    yield


app = FastAPI(
    title="Nilgiri Valley School API",
    summary="Read-only records for the SchoolOps agent.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(school.router, prefix="/school")
app.include_router(students.router, prefix="/school")
app.include_router(events.router, prefix="/school")
app.include_router(buses.router, prefix="/school")
app.include_router(attendance.router, prefix="/school")
app.include_router(policy.router, prefix="/school")
