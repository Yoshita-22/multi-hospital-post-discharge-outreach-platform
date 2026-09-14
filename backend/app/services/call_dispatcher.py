import uuid
import logging
import asyncio
from typing import List

from app.services.call_worker import call_worker

logger = logging.getLogger(__name__)

class CallDispatcher:
    def dispatch_calls(self, claimed_job_ids: List[uuid.UUID]) -> None:
        """
        Spawns background tasks to execute each claimed queue item via CallWorker.
        """
        for jid in claimed_job_ids:
            logger.info(f"[Dispatcher] Spawning background worker for claimed job: {jid}")
            asyncio.create_task(call_worker.execute(jid))
            
call_dispatcher = CallDispatcher()
