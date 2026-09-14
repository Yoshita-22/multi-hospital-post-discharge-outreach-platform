import uuid
from typing import List, Optional
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ehr import (
    Patient,
    Encounter,
    Discharge,
    Condition,
    Medication,
    Observation,
    CarePlan,
    Communication,
    Task,
)
from app.ehr.schemas import (
    PatientSchema,
    PatientName,
    EncounterSchema,
    DischargeSchema,
    ConditionSchema,
    MedicationSchema,
    ObservationSchema,
    CarePlanSchema,
    CommunicationSchema,
    TaskSchema,
    CommunicationCreate,
    TaskCreate,
    ObservationCreate,
    EncounterUpdate,
)


class MockEHR:
    """
    Mock EHR abstraction.
    Does NOT handle authorization/tenant checks.
    That is the responsibility of the HealthcareDataService.
    """

    async def get_patient(self, db: AsyncSession, patient_id: uuid.UUID) -> Optional[PatientSchema]:
        res = await db.execute(select(Patient).where(Patient.id == patient_id))
        patient = res.scalar_one_or_none()
        if not patient:
            return None

        telecom = []
        if patient.phone:
            telecom.append({"system": "phone", "value": patient.phone})
        if patient.email:
            telecom.append({"system": "email", "value": patient.email})

        return PatientSchema(
            id=str(patient.id),
            hospital_id=str(patient.hospital_id),
            name=[PatientName(given=[patient.first_name], family=patient.last_name)],
            gender=patient.gender,
            birthDate=patient.date_of_birth,
            telecom=telecom if telecom else None,
        )

    async def get_encounters(self, db: AsyncSession, patient_id: uuid.UUID) -> List[EncounterSchema]:
        res = await db.execute(select(Encounter).where(Encounter.patient_id == patient_id))
        encounters = res.scalars().all()
        
        return [
            EncounterSchema(
                id=str(e.id),
                hospital_id=str(e.hospital_id),
                patient_id=str(e.patient_id),
                status=e.status,
                class_={"code": e.care_setting} if e.care_setting else None,
                type=[{"text": e.encounter_type}] if e.encounter_type else None,
                period={"start": e.admission_time, "end": e.discharge_time},
            )
            for e in encounters
        ]

    async def get_discharges(self, db: AsyncSession, patient_id: uuid.UUID) -> List[DischargeSchema]:
        res = await db.execute(select(Discharge).where(Discharge.patient_id == patient_id))
        discharges = res.scalars().all()

        return [
            DischargeSchema(
                id=str(d.id),
                hospital_id=str(d.hospital_id),
                patient_id=str(d.patient_id),
                encounter_id=str(d.encounter_id),
                discharge_timestamp=d.discharge_timestamp,
                discharge_status=d.discharge_status,
                discharge_instructions=d.discharge_instructions,
                follow_up_required=d.follow_up_required,
                follow_up_start=d.follow_up_start,
                follow_up_deadline=d.follow_up_deadline,
                risk_level=d.risk_level,
                risk_indicators=d.risk_indicators,
            )
            for d in discharges
        ]

    async def get_conditions(self, db: AsyncSession, patient_id: uuid.UUID) -> List[ConditionSchema]:
        res = await db.execute(select(Condition).where(Condition.patient_id == patient_id))
        conditions = res.scalars().all()
        
        return [
            ConditionSchema(
                id=str(c.id),
                hospital_id=str(c.hospital_id),
                patient_id=str(c.patient_id),
                encounter_id=str(c.encounter_id) if c.encounter_id else None,
                clinicalStatus={"coding": [{"code": c.clinical_status}]} if c.clinical_status else None,
                code={"coding": [{"code": c.code, "display": c.display}]} if c.code else None,
                onsetDateTime=c.onset_date,
            )
            for c in conditions
        ]

    async def get_medications(self, db: AsyncSession, patient_id: uuid.UUID) -> List[MedicationSchema]:
        res = await db.execute(select(Medication).where(Medication.patient_id == patient_id))
        meds = res.scalars().all()
        
        return [
            MedicationSchema(
                id=str(m.id),
                hospital_id=str(m.hospital_id),
                patient_id=str(m.patient_id),
                encounter_id=str(m.encounter_id) if m.encounter_id else None,
                code={"text": m.name},
                status=m.status,
                dosageInstruction=[{"text": m.dosage, "route": {"text": m.route}, "timing": {"code": m.frequency}}],
                effectivePeriod={"start": m.start_date, "end": m.end_date},
            )
            for m in meds
        ]

    async def get_observations(self, db: AsyncSession, patient_id: uuid.UUID) -> List[ObservationSchema]:
        res = await db.execute(select(Observation).where(Observation.patient_id == patient_id))
        obs = res.scalars().all()
        
        return [
            ObservationSchema(
                id=str(o.id),
                hospital_id=str(o.hospital_id),
                patient_id=str(o.patient_id),
                encounter_id=str(o.encounter_id) if o.encounter_id else None,
                status=o.status,
                code={"coding": [{"code": o.code, "display": o.display}]} if o.code else None,
                valueQuantity={"value": o.value, "unit": o.unit},
                effectiveDateTime=o.observed_at,
            )
            for o in obs
        ]

    async def get_care_plans(self, db: AsyncSession, patient_id: uuid.UUID) -> List[CarePlanSchema]:
        res = await db.execute(select(CarePlan).where(CarePlan.patient_id == patient_id))
        plans = res.scalars().all()
        
        return [
            CarePlanSchema(
                id=str(cp.id),
                hospital_id=str(cp.hospital_id),
                patient_id=str(cp.patient_id),
                encounter_id=str(cp.encounter_id) if cp.encounter_id else None,
                status=cp.status,
                title=cp.title,
                description=cp.description,
                period={"start": cp.start_date, "end": cp.end_date},
            )
            for cp in plans
        ]

    # --- Write Operations ---

    async def create_communication(
        self, db: AsyncSession, hospital_id: uuid.UUID, patient_id: uuid.UUID, data: CommunicationCreate
    ) -> CommunicationSchema:
        comm = Communication(
            hospital_id=hospital_id,
            patient_id=patient_id,
            communication_type=data.communication_type,
            content=data.content,
            occurred_at=datetime.utcnow(),
        )
        db.add(comm)
        await db.flush()
        
        return CommunicationSchema(
            id=str(comm.id),
            hospital_id=str(comm.hospital_id),
            patient_id=str(comm.patient_id),
            status="completed",
            category=[{"text": comm.communication_type}],
            payload=[{"contentString": comm.content}],
            sent=comm.occurred_at,
        )

    async def create_task(
        self, db: AsyncSession, hospital_id: uuid.UUID, patient_id: uuid.UUID, data: TaskCreate
    ) -> TaskSchema:
        task = Task(
            hospital_id=hospital_id,
            patient_id=patient_id,
            task_type=data.task_type,
            description=data.description,
            due_at=data.due_at,
            status="requested",
        )
        db.add(task)
        await db.flush()
        
        return TaskSchema(
            id=str(task.id),
            hospital_id=str(task.hospital_id),
            patient_id=str(task.patient_id),
            status=task.status,
            description=task.description,
            executionPeriod={"end": task.due_at} if task.due_at else None,
        )

    async def create_observation(
        self, db: AsyncSession, hospital_id: uuid.UUID, patient_id: uuid.UUID, data: ObservationCreate
    ) -> ObservationSchema:
        obs = Observation(
            hospital_id=hospital_id,
            patient_id=patient_id,
            code=data.code,
            display=data.display,
            value=data.value,
            unit=data.unit,
            status=data.status,
            observed_at=datetime.utcnow(),
        )
        db.add(obs)
        await db.flush()
        
        return ObservationSchema(
            id=str(obs.id),
            hospital_id=str(obs.hospital_id),
            patient_id=str(obs.patient_id),
            status=obs.status,
            code={"coding": [{"code": obs.code, "display": obs.display}]},
            valueQuantity={"value": obs.value, "unit": obs.unit},
            effectiveDateTime=obs.observed_at,
        )

    async def update_encounter(
        self, db: AsyncSession, encounter_id: uuid.UUID, data: EncounterUpdate
    ) -> Optional[EncounterSchema]:
        res = await db.execute(select(Encounter).where(Encounter.id == encounter_id))
        encounter = res.scalar_one_or_none()
        if not encounter:
            return None
            
        if data.status is not None:
            encounter.status = data.status
        if data.care_setting is not None:
            encounter.care_setting = data.care_setting
            
        await db.flush()
        
        return EncounterSchema(
            id=str(encounter.id),
            hospital_id=str(encounter.hospital_id),
            patient_id=str(encounter.patient_id),
            status=encounter.status,
            class_={"code": encounter.care_setting} if encounter.care_setting else None,
            type=[{"text": encounter.encounter_type}] if encounter.encounter_type else None,
            period={"start": encounter.admission_time, "end": encounter.discharge_time},
        )

mock_ehr = MockEHR()
