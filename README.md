# Multi-Hospital Post-Discharge Outreach Platform

**Autonomous AI-Powered Patient Follow-Up, Clinical Triage & Hospital Outreach Operations Platform**

## 1. Overview

The **Multi-Hospital Post-Discharge Outreach Platform** is a multi-tenant healthcare operations platform designed to automate and coordinate post-discharge patient follow-up.

The platform enables hospitals to:

- Manage discharged patients
- Create post-discharge outreach campaigns
- Identify and prioritize eligible patients
- Schedule and process outbound calls
- Conduct AI-assisted patient outreach
- Capture structured conversation information
- Perform multi-agent clinical triage
- Identify cases requiring human attention
- Create escalation and follow-up tasks
- Record interactions through a Mock EHR
- Monitor campaign and hospital-level operations
- Maintain an auditable history of important actions

The platform is designed to behave as a **hospital outreach operations system rather than simply an AI voice agent**.

### Overall Workflow

```text
Hospital
   ↓
Patient Discharge Data
   ↓
Outreach Campaign
   ↓
Patient Eligibility
   ↓
Prioritization
   ↓
Outbound Queue
   ↓
AI Voice Outreach
   ↓
ConversationResult
   ↓
Clinical Triage
   ↓
Multi-Agent Assessment
   ↓
Consensus + Safety Rules
   ↓
Final Triage
   ↓
Routine / Attention / Urgent
   ↓
Follow-up / Human Review / Escalation
   ↓
Mock EHR / Staff Notification
   ↓
Campaign & Hospital Analytics
```
2. Key Features
🏥 Multi-Tenant Hospital Platform

Each hospital is treated as an independent tenant.

Tenant isolation applies to:

Users
Patients
Discharge records
Campaigns
Clinical protocols
Knowledge resources
Calls
Escalations
Notifications
Analytics
Configuration

The backend enforces tenant isolation rather than relying only on frontend filtering.

👥 Role-Based Access

The platform supports four roles:

Platform Admin
Hospital Admin
Campaign Manager
Clinical Reviewer

Each role has a different set of responsibilities and permissions.

👤 Patient & Discharge Management

The platform supports structured healthcare-oriented patient information, including:

Patient information
Encounter information
Discharge information
Conditions
Medications
Care plans
Observations
Follow-up requirements

The prototype supports simulated discharge data across multiple hospitals.

📢 Campaign Management

Campaign managers can:

Create campaigns
Configure campaign rules
Review eligible patients
Start campaigns
Pause campaigns
Resume campaigns
Monitor campaign progress
Review completed and failed calls
Monitor escalations
Re-prioritize campaign work
📋 Outbound Queue

The queue manages patient outreach work with support for:

Prioritization
Concurrency control
Retry handling
Backoff
No-answer handling
Busy/voicemail handling
Dropped-call handling
Callback handling
Maximum retry handling
Manual follow-up
Clinical cutoff handling
🤖 AI Clinical Triage

The platform uses multiple AI assessment components:
```

ConversationResult
       ↓
┌─────────────┬─────────────┬─────────────┐
│   Findings  │   Protocol  │   Safety    │
│    Agent    │    Agent    │    Agent    │
└─────────────┴─────────────┴─────────────┘
       ↓
Consensus
       ↓
Safety Rules
       ↓
TriageResult
```

The three agents independently analyze the patient conversation before the backend computes the final triage result.

🏥 Mock EHR

The platform provides a structured Mock EHR interface for:

Patient lookup
Encounter lookup
Discharge information
Observations
Conditions
Care-plan information
Communication records
Follow-up tasks
Escalations

The AI does not directly manipulate EHR/database tables.

Instead, healthcare operations follow:

```
AI Agent
   ↓
Structured Request
   ↓
Authorization
   ↓
Validation
   ↓
Healthcare Data Service
   ↓
Mock EHR
```
📊 Operational Analytics

The platform provides visibility into:

Pending calls
Active calls
Retries
Successful contacts
Failed contacts
Escalations
Campaign completion
System health
Clinical safety metrics
## 3. System Architecture

```text
                    ┌──────────────────────┐
                    │      Frontend        │
                    │ Hospital Operations  │
                    │         UI           │
                    └──────────┬───────────┘
                               │
                         HTTPS + JWT
                               │
                               ▼
                    ┌──────────────────────┐
                    │    FastAPI Backend   │
                    │                      │
                    │ Auth / RBAC          │
                    │ Tenant Context       │
                    │ Patients             │
                    │ Campaigns            │
                    │ Outreach             │
                    │ Triage               │
                    │ Analytics            │
                    └──────────┬───────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
        PostgreSQL         Scheduler       Call Worker
                                               │
                                               ▼
                                      Voice / Mock Provider
                                               │
                                               ▼
                                      ConversationResult
                                               │
                                               ▼
                                      Clinical Triage
                                               │
                         ┌─────────────────────┼──────────────────┐
                         ▼                     ▼                  ▼
                    Findings              Protocol             Safety
                     Agent                 Agent               Agent
                         └─────────────────────┼──────────────────┘
                                               ▼
                                      Consensus Engine
                                               │
                                               ▼
                                       Safety Rule Engine
                                               │
                                               ▼
                                          TriageResult
                                               │
                                               ▼
                                      Escalation Service
                                               │
                                               ▼
                                      Healthcare Data Service
                                               │
                                               ▼
                                           Mock EHR
```
```
AI and Healthcare Data Boundary

AI agents are separated from direct database/EHR access.

The intended boundary is:

AI Agent
   ↓
Structured Tool Request
   ↓
Authorization
   ↓
Validation
   ↓
Healthcare Data Service
   ↓
EHR Interface
```
##4. Technology Stack
Backend
Python
FastAPI
SQLAlchemy
PostgreSQL
Alembic
Pydantic
JWT Authentication
APScheduler
AI
Google Gemini
Multi-agent clinical assessment
Structured AI outputs
Voice
LiveKit Agents
Deepgram
Mock voice/call provider for prototype demonstration
Frontend
React
TypeScript
API-based communication with FastAPI
JWT authentication
Role-based UI
Development Tools
ChatGPT
Antigravity
Git
GitHub
##5. Project Structure
```
project/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── services/
│   │       ├── triage/
│   │       └── voice/
│   │
│   ├── alembic/
│   │   └── versions/
│   │
│   ├── requirements.txt
│   └── ...
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── types/
│   │   └── ...
│   └── ...
│
├── my-doctor-agent/
│   ├── agent.ts
│   ├── main.ts
│   └── ...
│
├── docs/
│   ├── architecture.md
│   ├── ai-tools.md
│   ├── ai-prompts.md
│   ├── product-ai.md
│   ├── safety-report.md
│   └── queue-design.md
│
├── .env.example
└── README.md
##6. Prerequisites
```
Before running the project locally, install:

Python 3.10+
Node.js 18+
PostgreSQL
Git
npm
pnpm

Optional services:

Google Gemini API
Deepgram
LiveKit
##7. Setup Instructions
Backend Setup

Clone the repository:

git clone <repository-url>
cd <project-directory>

Navigate to the backend:

cd backend

Create a virtual environment:

python -m venv venv
Windows
venv\Scripts\activate
Linux/macOS
source venv/bin/activate

Install dependencies:

pip install -r requirements.txt

Create the environment file:

cp .env.example .env

On Windows PowerShell:

Copy-Item .env.example .env

Configure the required environment variables in .env.

Run migrations:

alembic upgrade head

Start the backend:

uvicorn app.main:app --reload
Frontend Setup

Open another terminal:

cd frontend

Install dependencies:

npm install

Start the frontend:

npm run dev
LiveKit Agent Setup

The LiveKit agent is maintained as a separate TypeScript project.

Navigate to the agent:

cd my-doctor-agent

Install dependencies:

pnpm install

Configure the required API keys and LiveKit URL in .env.

Run the agent:

pnpm run dev

The prototype can use the Mock Call Provider when live voice infrastructure is not available.

##8. Environment Configuration

Create a .env file based on .env.example.

Example:

DATABASE_URL=your_database_url
SYNC_DATABASE_URL=your_sync_database_url

JWT_SECRET_KEY=your_secure_secret_key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

GEMINI_API_KEY=your_gemini_api_key

DEEPGRAM_API_KEY=your_deepgram_api_key

LIVEKIT_URL=your_livekit_url
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret
Security

Do not commit:

.env
API keys
Database passwords
JWT secrets
LiveKit secrets
AI credentials

Only commit .env.example containing placeholder values.

##9. Database Setup
PostgreSQL

The application uses PostgreSQL for persistent application data.

Create a PostgreSQL database for local development.

Example:

CREATE DATABASE post_discharge_outreach;

Configure the database connection in .env:

DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/post_discharge_outreach
Alembic Migrations

Alembic is used to manage database schema migrations.

Apply migrations
alembic upgrade head
Create a migration

After changing SQLAlchemy models:

alembic revision --autogenerate -m "Describe your changes"

Review the generated migration and then apply it:

alembic upgrade head
Roll back the latest migration
alembic downgrade -1
View migration history
alembic history
Show current database revision
alembic current
##10. Mock EHR Setup

The prototype uses a Mock EHR to demonstrate healthcare-system integration without requiring access to a real hospital EHR.

The Mock EHR provides structured operations such as:

Patient Lookup
      ↓
Encounter Lookup
      ↓
Discharge Information
      ↓
Clinical Information
      ↓
Communication / Task / Escalation

The AI does not directly access EHR tables.

Instead:

AI Agent
   ↓
Structured Request
   ↓
Authorization
   ↓
Validation
   ↓
Healthcare Data Service
   ↓
Mock EHR

This abstraction allows the Mock EHR to be replaced with a real EHR integration in a future production implementation.

11. Queue Simulation

The outbound queue represents patients waiting for post-discharge outreach.

Queue
Eligible Patient
      ↓
Priority Calculation
      ↓
Outbound Queue
      ↓
Queue Scheduler
      ↓
Call Worker
      ↓
Call Attempt

The queue considers factors such as:

Patient risk
Discharge timing
Campaign rules
Calling capacity
Concurrency

The queue worker limits the number of calls processed concurrently according to the configured calling capacity.

This prevents the system from attempting unlimited simultaneous calls.

Retry

Failed or unanswered calls can be scheduled for another attempt according to retry configuration.

The queue supports:

Retry count
Retry scheduling
Backoff
Maximum retry attempts
No-answer handling
Busy/voicemail handling
Dropped-call handling
Callback

If a patient requests a callback, the system can record the callback requirement and schedule follow-up work.

The callback information is preserved as part of the outreach workflow.

12. AI / Clinical Triage Demo

The platform uses a multi-agent clinical triage workflow.
```
ConversationResult
       │
       ├───────────────┐
       ▼               ▼
 Findings Agent    Protocol Agent
       │               │
       └───────┬───────┘
               │
               ▼
          Safety Agent
               │
               ▼
        Consensus Engine
               │
               ▼
       Safety Rule Engine
               │
               ▼
          TriageResult
```
Findings Agent

Extracts information explicitly reported by the patient.

Protocol Agent

Evaluates the extracted information against the campaign's configured protocol.

Safety Agent

Identifies potential safety concerns and red flags.

Consensus

The assessments are combined using deterministic backend logic.

The primary triage levels are:

ROUTINE < ATTENTION < URGENT
Demo Scenarios
🟢 Routine
"I am feeling well and recovering normally."

Expected:

ROUTINE
🟡 Attention
"My ankles have become more swollen over the last two days."

Expected:

ATTENTION
🔴 Urgent
"I have severe chest pain and difficulty breathing."

Expected:

URGENT

These are illustrative demonstration scenarios only and are not medically validated clinical protocols.

13. Running the Application

Start PostgreSQL first.

Then start the backend:

cd backend
uvicorn app.main:app --reload

Start the frontend in another terminal:

cd frontend
npm run dev

If using the LiveKit agent:

cd my-doctor-agent
pnpm run dev

The frontend communicates with the FastAPI backend through the configured API base URL.

FastAPI's interactive API documentation can be accessed through the backend Swagger endpoint during development.

##14. Testing Instructions

The application should be tested across the following areas.

Authentication

Test:

Login
JWT validation
Unauthorized access
Invalid token handling
Expired token handling
Authorization

Test:

Role-based access
Protected routes
Permission checks
Tenant Isolation

Verify that users belonging to one hospital cannot access another hospital's data.

Example:

Hospital A
   │
   ├── Patients ✓
   ├── Campaigns ✓
   └── Protocols ✓

   ✕ Hospital B Patients
   ✕ Hospital B Campaigns
   ✕ Hospital B Protocols
   ✕ Hospital B Calls

Tenant isolation must be enforced at the backend/service layer.

Queue

Test:

Prioritization
Concurrency
Retry
Backoff
No-answer handling
Callback
Maximum retries
AI / Triage

Test:

Routine scenario
Attention scenario
Urgent scenario
Agent disagreement
Safety override
Protocol rule matching
Agent failure
Idempotency
EHR

Test:

Patient lookup
Encounter lookup
Documentation
Follow-up task
Escalation
EHR write operations


##15. Demo Credentials

The following credentials are intended only for the local/demo environment.

Role	Email	Password
Platform Admin	admin@platform.com	PlatformAdmin@2026
Hospital Admin	seema@vedhanta.com	SecurePass123!
Campaign Manager	renu@vedhanta.com	campaignPass123!

Important: Change or disable demo credentials before any production deployment.

## 16. Known Limitations

- The voice workflow may use a Mock Call Provider instead of production telephony.
- The Mock EHR is simulated and is not connected to a real hospital EHR.
- Clinical protocols and demo scenarios are illustrative and not medically validated.
- AI-generated outputs may be affected by ambiguous or incomplete patient responses.
- Production-scale voice infrastructure has not been fully implemented.
- Full production FHIR interoperability is not implemented.
- Hospital notification channels are simulated.
- The current queue/scheduler implementation is intended for prototype-scale workloads.
- Comprehensive production clinical validation and regulatory review are outside the prototype scope.
- Language and regional dialect coverage may be limited.

---

## 17. Future Enhancements

Potential future enhancements include:


- Production telephony and voice infrastructure
- Scalable distributed workers
- More comprehensive multilingual support
- Clinical validation of protocols
- Enhanced observability and monitoring
- Advanced hospital analytics
- Production-grade notification integrations
- Comprehensive security and compliance validation
- Clinician feedback loops for improving AI assessments
- Real-time operational dashboards
- Advanced AI evaluation and monitoring
- Improved interoperability with external healthcare systems
