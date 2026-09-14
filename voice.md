Implement the Conversation / Voice Intake Agent for the post-discharge healthcare outreach platform.

IMPORTANT ARCHITECTURE:

The Conversation Agent is responsible for conducting the patient conversation and capturing what the patient says.

It is NOT responsible for:
- Clinical risk assessment
- Diagnosis
- Triage
- Escalation decisions
- Direct database access

Those responsibilities belong to downstream Triage/Escalation components.

==================================================
1. INPUT TO CONVERSATION AGENT
==================================================

The agent should receive a structured context containing:

A. Patient Context
- patient_id
- patient name
- preferred language/contact preference
- relevant conditions
- relevant discharge information
- relevant medications/care-plan information
- follow-up requirements

Do NOT dump the entire EHR into the LLM. Only provide the patient information relevant to this outreach.

B. Outreach Context
- call_id
- campaign_id
- campaign name
- outreach purpose
- attempt number
- discharge date / days since discharge
- callback information if applicable

C. Clinical Protocol
- protocol name/version
- questions to ask
- question IDs
- allowed conversation scope
- clarification guidance
- completion conditions

The protocol should control WHAT information needs to be collected.
The LLM should control HOW the conversation naturally happens.

D. Conversation State
- current stage
- current question
- completed questions
- remaining questions
- previous responses
- symptoms reported
- uncertainties
- clarification count
- callback_requested
- callback_time
- patient_reached
- transcript

==================================================
2. CONVERSATION LOOP
==================================================

The voice pipeline should conceptually work as:

Patient speaks
    ↓
STT
    ↓
Conversation Agent / LLM
    ↓
Structured response
    ↓
TTS
    ↓
Patient

The LLM must both:

1. Generate the next response to the patient.
2. Extract/capture important information from the patient's latest response.

Example:

Patient:
"I've been okay, but my ankles have been more swollen and I missed one of my tablets."

LLM output should contain:

- response to patient
- captured symptoms
- medication/adherence information
- relevant patient response
- conversation action
- updated conversational information

The LLM must NOT determine:
- high/medium/low clinical risk
- diagnosis
- emergency status
- escalation decision

Those belong to the Triage Agent.

==================================================
3. CONVERSATION STATE MACHINE
==================================================

Implement the conversation using explicit stages:

INTRO
VERIFY
PURPOSE
QUESTIONING
CLARIFY
CALLBACK
TRANSFER
COMPLETE
DECLINED
INTERRUPTED

Typical flow:

INTRO
  ↓
VERIFY
  ↓
PURPOSE
  ↓
QUESTIONING
  ↓
UNDERSTAND PATIENT RESPONSE
  ↓
 ┌───────────────────────┐
 │                       │
Clear response       Unclear response
 │                       │
 ↓                       ↓
Capture information    CLARIFY
 │                       │
 └───────────┬───────────┘
             ↓
      More questions?
       /           \
     YES            NO
      ↓              ↓
QUESTIONING       COMPLETE

The conversation may branch to:

CALLBACK
TRANSFER
DECLINED
INTERRUPTED

when appropriate.

==================================================
4. STRUCTURED LLM OUTPUT
==================================================

Do NOT allow the LLM to return only free-form text.

Create a structured output similar to:

{
  "response": "Can you tell me whether the breathing problem happens while resting or only when walking?",

  "action": "ASK_FOLLOWUP",

  "captured_information": {
    "responses": {},
    "symptoms": [],
    "medication_information": {},
    "follow_up_information": {},
    "concerns": []
  },

  "uncertainties": [],

  "callback": {
    "requested": false,
    "requested_time": null
  },

  "conversation": {
    "next_stage": "QUESTIONING",
    "current_question_id": "shortness_of_breath"
  }
}

Use enums rather than arbitrary strings wherever practical.

Possible actions:

ASK_QUESTION
ASK_FOLLOWUP
CLARIFY
COMPLETE
REQUEST_CALLBACK
TRANSFER
DECLINED
INTERRUPTED

==================================================
5. INFORMATION CAPTURE
==================================================

The agent should capture factual information explicitly stated by the patient.

Examples:

Patient:
"I've been feeling dizzy since yesterday."

Capture:

{
  "symptoms": [
    {
      "name": "dizziness",
      "details": "started yesterday"
    }
  ]
}

Patient:
"I forgot to take my medication this morning."

Capture:

{
  "medication_information": {
    "adherence_issue": "missed_dose",
    "details": "missed morning dose"
  }
}

Do NOT infer information that the patient did not state.

For example, do NOT convert:

"I'm feeling tired"

into:

"Patient has worsening heart failure."

That interpretation belongs to Triage.

==================================================
6. CLARIFICATION
==================================================

If the patient's answer is ambiguous, incomplete, or unclear:

DO NOT GUESS.

Ask a natural clarification question.

Example:

Patient:
"Yeah, I've had some problems."

Agent:
"Could you tell me a little more about what problems you've been experiencing?"

Limit repeated clarification attempts where appropriate.

==================================================
7. NATURAL CONVERSATION
==================================================

The agent should not sound like a rigid questionnaire.

It should:

- acknowledge patient responses naturally
- ask one appropriate question at a time
- avoid repeatedly asking information already provided
- recognize when the patient answers a future question early
- capture important unsolicited information
- ask clarification questions when needed
- avoid unnecessary repetition
- remain within the campaign protocol
- end the conversation appropriately

Example:

Protocol asks:
1. Recovery
2. Breathing
3. Swelling
4. Medication
5. Follow-up appointment

Patient says during question 1:

"I'm doing okay except my ankles are swollen."

The agent should capture the swelling information and should NOT later ask:

"Have you noticed any swelling?"

unless clarification is necessary.

==================================================
8. CONVERSATION RESULT
==================================================

When the conversation ends, produce a ConversationResult containing:

- call_id
- patient_id
- campaign_id
- outcome
- patient_reached
- responses
- symptoms_reported
- uncertainties
- callback_requested
- callback_time
- transcript
- summary
- started_at
- completed_at

Possible outcomes:

COMPLETED
CALLBACK_REQUESTED
PATIENT_DECLINED
INTERRUPTED
TRANSFERRED
NO_ANSWER

Do NOT include:
- diagnosis
- clinical risk level
- triage result
- escalation decision

Those will be produced downstream.

==================================================
9. SECURITY / DATA ACCESS
==================================================

The LLM must NEVER directly access PostgreSQL or the EHR database.

Use application/service-layer interfaces:

Conversation Agent
    ↓
Controlled tool/service interface
    ↓
Healthcare Data Service
    ↓
Mock EHR / EHR interface

All patient context supplied to the agent must already be authorized and scoped to the current hospital/tenant.

Enforce tenant isolation.

==================================================
10. IMPLEMENTATION REQUIREMENTS
==================================================

Before coding:

1. Inspect the existing project structure.
2. Reuse existing models, schemas, services and enums where appropriate.
3. Do not duplicate existing functionality.
4. Do not introduce Celery/Redis unless already required by the project.
5. Keep the implementation suitable for the current prototype.
6. Make the LLM provider replaceable through an interface.
7. Keep STT and TTS provider integrations replaceable through interfaces.
8. For development, allow mocked STT/TTS/call-provider implementations.
9. Add unit tests for the ConversationState transitions and structured LLM output validation.
10. Do not modify unrelated modules.

The final architecture should allow:

Mock Call Provider
      ↓
STT
      ↓
Conversation Agent
      ↓
TTS

while keeping the interfaces replaceable later with real telephony/STT/TTS providers.

==================================================
11. IMPORTANT BOUNDARY
==================================================

Maintain this separation throughout the implementation:

Conversation Agent:
"What did the patient say?"

Triage Agent:
"What might that information mean clinically?"

Escalation:
"What should the system do?"

Do not merge these responsibilities into one LLM.

After implementation, provide:
- files created/modified
- architecture implemented
- API/service interfaces
- ConversationState schema
- ConversationResult schema
- example LLM structured output
- tests added
- any assumptions or TODOs