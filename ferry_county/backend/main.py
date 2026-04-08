from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings
from backend.routers import (
    attachments,
    compliance,
    emergency_admin,
    gis,
    health,
    infrastructure,
    public,
    roads,
    sentinel,
    sync,
    tracks,
    treatments,
    waypoints,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    sched = None
    s = get_settings()
    if s.sentinel_scheduler_enabled and not s.testing:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
        from apscheduler.triggers.interval import IntervalTrigger

        from backend.services.sentinel import red_flag_check_job, scheduled_scan_job

        sched = BackgroundScheduler()
        sched.add_job(
            scheduled_scan_job,
            CronTrigger(month="5-10", hour="0,6,12,18", minute=0),
            id="sentinel_fire_season",
            replace_existing=True,
        )
        sched.add_job(
            red_flag_check_job,
            IntervalTrigger(hours=1),
            id="sentinel_red_flag_ping",
            replace_existing=True,
        )
        sched.start()
    yield
    if sched is not None:
        sched.shutdown(wait=False)


app = FastAPI(title="Ferry County CWDG", version="0.1.0", lifespan=lifespan)

_settings = get_settings()
_origins = [o.strip() for o in _settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins or ["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(public.router)
app.include_router(emergency_admin.router)
app.include_router(infrastructure.router)
app.include_router(attachments.router)
app.include_router(roads.router)
app.include_router(tracks.router)
app.include_router(waypoints.router)
app.include_router(treatments.router)
app.include_router(gis.router)
app.include_router(compliance.router)
app.include_router(sentinel.router)
app.include_router(sync.router)
