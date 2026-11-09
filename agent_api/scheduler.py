"""APScheduler configuration for morning operational workflows."""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from agent_api.services.morning_workflow import run_morning_workflow

scheduler = BackgroundScheduler()


def scheduled_morning_job() -> None:
    """Invoked by APScheduler at 06:00 Mon-Sat on school days."""
    try:
        run_morning_workflow()
    except Exception as exc:
        print(f"[Scheduler] Error running morning workflow: {exc}")


def init_scheduler() -> BackgroundScheduler:
    """Add recurring cron trigger and start scheduler."""
    if not scheduler.running:
        trigger = CronTrigger(day_of_week="mon-sat", hour=6, minute=0, timezone="Asia/Kolkata")
        scheduler.add_job(
            scheduled_morning_job,
            trigger=trigger,
            id="morning_operational_check",
            replace_existing=True,
        )
        scheduler.start()
    return scheduler


def shutdown_scheduler() -> None:
    """Gracefully shutdown background scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
