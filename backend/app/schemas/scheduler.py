from pydantic import BaseModel

class SchedulerRunResult(BaseModel):
    campaigns_checked: int
    campaigns_with_capacity: int
    jobs_considered: int
    jobs_claimed: int
