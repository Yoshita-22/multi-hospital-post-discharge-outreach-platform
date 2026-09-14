You are working on my Multi-Hospital Post-Discharge Outreach Platform.

I already have these parts implemented:

1. Campaign creation
2. Campaign validation
3. Patient eligibility evaluation
4. Patient prioritization
5. Outbound queue creation
6. QueueScheduler.run_once(db, tenant) exists and currently runs only when:
   POST /api/v1/scheduler/run
   is called manually.

Now implement the complete Queue Scheduler execution flow and Call Worker architecture.

IMPORTANT:
Before changing anything, inspect the existing project structure, models, schemas, services, repositories, database/session handling, tenant/authentication logic, campaign lifecycle, outbound queue implementation, scheduler implementation, and existing call-related abstractions.

DO NOT create duplicate models/services if equivalent implementations already exist.
Reuse existing code and follow the project's current conventions.

==================================================
PART 1 — QUEUE SCHEDULER
==================================================

The Queue Scheduler's responsibility is:

"Determine which waiting outbound queue jobs are currently allowed to use available calling capacity."

The Scheduler must NOT:
- evaluate eligibility again
- calculate campaign eligibility
- recalculate patient prioritization
- perform clinical reasoning
- make the actual voice call
- directly execute the AI conversation

Eligibility and prioritization have already happened before a patient reaches the queue.

The scheduler should operate on already-created outbound queue items.
--------------------------------------------------
 Scheduler output
--------------------------------------------------

run_once() should return a useful result such as:

{
    "campaigns_processed": ...,
    "jobs_considered": ...,
    "jobs_claimed": ...,
    "jobs_skipped": ...,
    "available_capacity": ...,
    "timestamp": ...
}

Adapt this to existing response schemas if appropriate.

Do not expose unnecessary patient information in logs/responses.

==================================================
PART 2 — PERIODIC SCHEDULER TRIGGER
==================================================

The current scheduler only runs when:

POST /api/v1/scheduler/run

is manually called.

Now add background periodic execution.

Use APScheduler unless the project already has an established background scheduler framework.

Do NOT introduce Celery + Redis just for this prototype.

--------------------------------------------------
1. Periodic execution
--------------------------------------------------

Configure an environment variable such as:

SCHEDULER_INTERVAL_SECONDS=30

Default to a reasonable prototype value such as 30 or 60 seconds.

The scheduler should periodically invoke:

QueueScheduler.run_once(...)

Do not duplicate scheduling logic inside APScheduler.

APScheduler is only a TRIGGER.

QueueScheduler contains the actual scheduling algorithm.

Architecture:

APScheduler
    ↓
trigger
    ↓
QueueScheduler.run_once()
    ↓
database

--------------------------------------------------
2. FastAPI lifecycle
--------------------------------------------------

Start the background scheduler through the application's existing FastAPI lifespan/startup mechanism.

Stop it cleanly during application shutdown.

Do NOT start scheduler threads at module import time.

Avoid creating multiple scheduler instances accidentally during imports/reloads.

Make development behavior safe when using reload mode.

--------------------------------------------------
3. Prevent overlapping scheduler runs
--------------------------------------------------

Configure APScheduler so the same scheduled job does not unnecessarily overlap.

For example:

max_instances = 1
coalesce = True

or the equivalent supported by the installed APScheduler version.

However, database-level locking MUST still protect queue claiming.

Do not rely only on APScheduler configuration for concurrency safety.

--------------------------------------------------


==================================================
PART 3 — CALL WORKER
==================================================

Now implement the Call Worker.

The worker is the EXECUTOR.

The scheduler decides:

"Patient X gets a call slot."

The worker decides:

"Execute Patient X's call."

The worker must NOT decide:
- eligibility
- priority
- scheduling
- clinical triage
- escalation reasoning

Those belong to other components.

--------------------------------------------------
1. Worker input
--------------------------------------------------

Worker receives a queue job that has already been claimed by Scheduler.

Example:

queue_id
campaign_id
patient_id
hospital_id
priority_score
attempt_count
max_attempts

--------------------------------------------------
2. Claim safety
--------------------------------------------------

Worker must only execute jobs in a valid claimed state.

Do not allow two workers to execute the same queue item.

If the queue item is already being executed/completed, safely ignore/return.

Reuse existing status values.

Expected lifecycle should conceptually be:

PENDING
   ↓
CLAIMED
   ↓
IN_PROGRESS
   ↓
COMPLETED

or:

IN_PROGRESS
   ↓
RETRY_PENDING
   ↓
CLAIMED
   ↓
IN_PROGRESS

or:

IN_PROGRESS
   ↓
FAILED

Adapt exact names to existing models.

--------------------------------------------------
3. Attempt count
--------------------------------------------------

When an actual call attempt begins:

increment attempt_count exactly once.

Do not increment it multiple times because of internal retries or duplicate worker execution.

Make the operation transaction-safe.

--------------------------------------------------
4. Retrieve patient context
--------------------------------------------------

Worker should retrieve the information needed to perform the outreach through the existing controlled healthcare/EHR service boundary.

Do NOT give the AI arbitrary direct database access.

Use the existing healthcare data service/EHR abstraction if implemented.

Patient context may include:

- patient identity
- contact information
- discharge information
- conditions
- medications
- care plan
- follow-up requirements
- relevant observations
- preferred contact information

Enforce:

patient.hospital_id == queue.hospital_id == campaign.hospital_id == tenant.hospital_id

Do not allow cross-hospital access.

--------------------------------------------------
5. Voice provider abstraction
--------------------------------------------------

Create/reuse a pluggable interface such as:

VoiceCallProvider

or

VoiceCallService

The worker should depend on the interface, NOT a hard-coded telephony vendor.

For the prototype, implement a MockVoiceCallProvider if an actual provider is not yet integrated.

Example conceptual interface:

start_call(...)
    -> call/session identifier

wait_for_result(...)
    -> CallResult

or an equivalent async/event-driven abstraction appropriate to the existing architecture.

Do not unnecessarily couple the worker to Twilio/another vendor unless the project already uses one.

--------------------------------------------------
6. Call execution
--------------------------------------------------

The worker should:

1. load claimed queue job
2. validate tenant/hospital
3. mark IN_PROGRESS
4. increment attempt count
5. create/update call record
6. retrieve allowed patient context
7. invoke VoiceCallProvider
8. receive call result
9. persist outcome
10. update queue status
11. commit transaction
12. trigger scheduler

The worker should be able to run multiple jobs concurrently.

Do not execute calls sequentially if capacity allows multiple concurrent calls.

--------------------------------------------------
7. Call outcomes
--------------------------------------------------

Inspect existing PRD/models/enums first.

Reuse existing call outcome/status definitions.

If they do not exist yet, support a minimal extensible set such as:

PATIENT_REACHED
NO_ANSWER
BUSY
CALL_FAILED
CALLBACK_REQUESTED

Do not invent unnecessary clinical outcome types.

Clinical triage should be a separate step.

--------------------------------------------------
8. Successful call

For example:

PATIENT_REACHED

should result in:

queue.status = COMPLETED

and persist the call/outreach result.

If the conversation itself produces clinical information, store it through the appropriate conversation/documentation/triage service.

Do not put clinical reasoning directly into CallWorker.

--------------------------------------------------
9. Retryable outcomes

For:

NO_ANSWER
BUSY
temporary provider failure

if attempts remain:

queue.status = RETRY_PENDING

and set:

next_attempt_at

using a simple documented retry backoff.

Example:

attempt 1 -> retry after 5 minutes
attempt 2 -> retry after 15 minutes
attempt 3 -> no retry

Adapt to existing PRD configuration if available.

Do not exceed max_attempts.

--------------------------------------------------
10. Exhausted attempts

If:

attempt_count >= max_attempts

then:

queue.status = FAILED

Do not schedule another attempt.

The final outcome should be persisted for reporting/audit.

--------------------------------------------------
11. Callback requested

If patient requests a callback:

- persist callback information
- if callback time is known, set next_attempt_at appropriately
- use RETRY_PENDING or the project's existing callback status
- do not call before requested callback time

Follow existing schema if callback support already exists.

--------------------------------------------------
12. Provider exception

If VoiceCallProvider throws an exception:

- capture/log the error safely
- persist the failed attempt
- determine whether retry is allowed
- schedule retry if attempts remain
- otherwise mark FAILED
- do not leave queue permanently stuck in IN_PROGRESS

Make sure unexpected exceptions cannot silently lose the queue item.

--------------------------------------------------
13. Stale IN_PROGRESS / CLAIMED jobs

Think about application crashes.

Example:

Worker claims job
   ↓
application crashes
   ↓
job remains CLAIMED/IN_PROGRESS forever

Implement a simple recovery strategy if the current model supports timestamps such as updated_at/last_attempt_at.

Do not build an overly complex distributed job system.

At minimum, document how stale jobs are detected/recovered.

If implementing recovery, ensure a job cannot be duplicated while another worker is still legitimately executing it.

==================================================
PART 4 — WORKER + SCHEDULER INTEGRATION
==================================================

The final architecture should be:

                  Campaign
                     ↓
                Eligibility
                     ↓
                Prioritization
                     ↓
                Queue Creation
                     ↓
              OUTBOUND QUEUE
                     ↓
              Queue Scheduler
                     ↓
              PENDING → CLAIMED
                     ↓
                 WORKER
                     ↓
              Voice Call Provider
                     ↓
              AI Voice Conversation
                     ↓
                  Outcome
                     ↓
           ┌─────────┴─────────┐
           ↓                   ↓
       COMPLETED          RETRY_PENDING
           ↓                   ↓
       slot freed         next_attempt_at
           ↓                   ↓
           └──────────┬────────┘
                      ↓
                DB COMMIT
                      

The scheduler is responsible for selecting jobs.

The worker is responsible for executing jobs.

==================================================
PART 5 — ASYNC/BACKGROUND DESIGN

Do not make every function async merely because calls are long-running.

Keep responsibilities separated.

HTTP API:

POST /api/v1/scheduler/run

should return quickly.

Periodic scheduler:

APScheduler
↓
QueueScheduler.run_once()

Worker:

long-running call execution should happen outside the request lifecycle.

Use the project's existing async/background architecture where appropriate.

If no worker infrastructure exists, implement a clean prototype abstraction that can later be replaced by a real job queue.

Do NOT add Celery/Redis unless absolutely necessary.

Database sessions:

Each background scheduler/worker execution should obtain its own database session.

Never reuse a request-scoped SQLAlchemy session across background tasks.

==================================================
PART 6 — API

Keep the existing manual endpoint:

POST /api/v1/scheduler/run

for development/testing.

It should invoke the same:

QueueScheduler.run_once()

used by the background scheduler.

There must be exactly ONE scheduling algorithm.

Manual API and APScheduler must not have separate logic.

If appropriate, add a development-only endpoint for manually executing a specific worker job, but do not expose unsafe production behavior.

==================================================
PART 7 — AUDIT / OBSERVABILITY

Reuse the existing audit/event system.

At minimum log/audit important transitions:

scheduler started
scheduler run
jobs considered
jobs claimed
worker started
call started
call completed
retry scheduled
call failed
queue completed


Logs must include identifiers such as:

tenant_id
hospital_id
campaign_id
queue_id
patient_id

but DO NOT log sensitive clinical information, phone numbers, conversation transcripts, or other unnecessary PHI.

Follow existing PHI/security logging conventions.

==================================================
PART 9 — TESTS

Add tests for the following.

Scheduler:

pending job inside calling window is selected
job outside calling window is not selected
scheduled_at in future is not selected
next_attempt_at in future is not selected
exhausted retry job is not selected
campaign capacity is respected
active calls reduce available capacity
higher scheduling score is selected first
deterministic tie-breaking works
multiple campaigns respect individual capacity
hospital/tenant isolation works
concurrent scheduler executions cannot claim same job
manual API invokes run_once
periodic trigger invokes run_once
scheduler does not overlap unnecessarily

Worker:

claimed job becomes IN_PROGRESS
attempt_count increments exactly once
successful call becomes COMPLETED
NO_ANSWER schedules retry
BUSY schedules retry
retry exhaustion becomes FAILED
provider exception is handled
callback request stores callback time
worker cannot execute another hospital's job
multiple workers cannot execute the same job
stale execution behavior is handled/documented
==================================================
PART 10 — IMPORTANT IMPLEMENTATION RULES
Inspect existing code first.
Reuse existing models/enums/services.
Do not duplicate functionality.
Do not rewrite the Eligibility Engine.
Do not rewrite the Priority Engine.
Do not put clinical reasoning inside the worker.
Do not let AI directly access arbitrary database tables.
Do not exceed campaign calling capacity.
Do not allow duplicate queue execution.
Use PostgreSQL transaction/locking for concurrency safety.
Maintain strict hospital/tenant isolation.
Scheduler selects; Worker executes.
Periodic scheduler is the reliability backstop.
Call-completion trigger provides low-latency slot filling.
Scheduler must never make the actual voice call.
Worker must not decide which patient should be called next.
Do not introduce unnecessary infrastructure.
Keep the implementation prototype-friendly but architecturally extensible.
==================================================
FINAL DELIVERABLE

After implementation, give me:

Files created
Files modified
Database/model changes
Scheduler flow
Worker flow
Queue state transitions
How periodic execution works
How call-completion triggers scheduling
How concurrency is protected
How tenant isolation is enforced
API endpoint(s)
Environment variables added
Tests added and their results
Any assumptions or remaining TODOs