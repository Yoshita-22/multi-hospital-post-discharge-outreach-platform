import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.db.database import AsyncSessionLocal
from app.services.scheduler_service import queue_scheduler

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

async def scheduled_queue_run():
    """
    Periodic job invoked by APScheduler.
    """
    logger.info("Executing periodic System-Wide Queue Scheduler...")
    try:
        async with AsyncSessionLocal() as db:
            await queue_scheduler.run_all(db)
    except Exception as e:
        logger.error(f"Error in scheduled_queue_run: {e}")

def start_scheduler(interval_seconds: int = 30):
    scheduler.add_job(
        scheduled_queue_run,
        trigger=IntervalTrigger(seconds=interval_seconds),
        id="queue_scheduler_job",
        name="System-wide Outbound Queue Dispatcher",
        replace_existing=True,
        coalesce=True,
        max_instances=1
    )
    scheduler.start()
    logger.info(f"APScheduler started. Queue checks every {interval_seconds}s.")

def stop_scheduler():
    scheduler.shutdown()
    logger.info("APScheduler stopped.")
