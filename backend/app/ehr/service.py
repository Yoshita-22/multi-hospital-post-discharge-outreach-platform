import uuid
import random
from typing import List, Optional
from datetime import datetime, timedelta, date
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.tenant_context import TenantContext
from app.services.audit_service import audit_service
from app.ehr.schemas import (
    PatientSchema,
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
    OutreachOutcomeCreate,
)
from app.ehr.mock_ehr import mock_ehr
from app.models.ehr import (
    Patient,
    Encounter,
    Discharge,
    Condition,
    Medication,
    Observation,
    CarePlan,
)


class HealthcareDataService:
    async def _verify_patient_access(self, db: AsyncSession, patient_id: uuid.UUID, tenant: TenantContext):
        """Enforce tenant isolation."""
        res = await db.execute(select(Patient.hospital_id).where(Patient.id == patient_id))
        hospital_id = res.scalar_one_or_none()
        
        if not hospital_id:
            raise HTTPException(status_code=404, detail="Patient not found")
            
        if not tenant.can_access_hospital(hospital_id):
            raise HTTPException(status_code=403, detail="Access denied to this patient record")
            
        return hospital_id

    async def _verify_encounter_access(self, db: AsyncSession, encounter_id: uuid.UUID, tenant: TenantContext):
        res = await db.execute(select(Encounter.hospital_id).where(Encounter.id == encounter_id))
        hospital_id = res.scalar_one_or_none()
        
        if not hospital_id:
            raise HTTPException(status_code=404, detail="Encounter not found")
            
        if not tenant.can_access_hospital(hospital_id):
            raise HTTPException(status_code=403, detail="Access denied to this encounter record")
            
        return hospital_id

    async def get_patient(self, db: AsyncSession, patient_id: uuid.UUID, tenant: TenantContext) -> PatientSchema:
        hospital_id = await self._verify_patient_access(db, patient_id, tenant)
        
        await audit_service.log_event(
            db=db,
            action="EHR_PATIENT_READ",
            actor_user_id=tenant.user_id,
            hospital_id=assigned_hospital_id,
            resource_type="PATIENT",
            resource_id=patient_id,
        )
        return await mock_ehr.get_patient(db, patient_id)

    async def get_encounters(self, db: AsyncSession, patient_id: uuid.UUID, tenant: TenantContext) -> List[EncounterSchema]:
        hospital_id = await self._verify_patient_access(db, patient_id, tenant)
        await audit_service.log_event(db, "EHR_ENCOUNTER_READ", tenant.user_id, hospital_id, "PATIENT", patient_id)
        return await mock_ehr.get_encounters(db, patient_id)

    async def get_discharges(self, db: AsyncSession, patient_id: uuid.UUID, tenant: TenantContext) -> List[DischargeSchema]:
        hospital_id = await self._verify_patient_access(db, patient_id, tenant)
        await audit_service.log_event(db, "EHR_DISCHARGE_READ", tenant.user_id, hospital_id, "PATIENT", patient_id)
        return await mock_ehr.get_discharges(db, patient_id)

    async def get_conditions(self, db: AsyncSession, patient_id: uuid.UUID, tenant: TenantContext) -> List[ConditionSchema]:
        hospital_id = await self._verify_patient_access(db, patient_id, tenant)
        return await mock_ehr.get_conditions(db, patient_id)

    async def get_medications(self, db: AsyncSession, patient_id: uuid.UUID, tenant: TenantContext) -> List[MedicationSchema]:
        hospital_id = await self._verify_patient_access(db, patient_id, tenant)
        return await mock_ehr.get_medications(db, patient_id)

    async def get_observations(self, db: AsyncSession, patient_id: uuid.UUID, tenant: TenantContext) -> List[ObservationSchema]:
        hospital_id = await self._verify_patient_access(db, patient_id, tenant)
        await audit_service.log_event(db, "EHR_OBSERVATION_READ", tenant.user_id, hospital_id, "PATIENT", patient_id)
        return await mock_ehr.get_observations(db, patient_id)

    async def get_care_plans(self, db: AsyncSession, patient_id: uuid.UUID, tenant: TenantContext) -> List[CarePlanSchema]:
        hospital_id = await self._verify_patient_access(db, patient_id, tenant)
        return await mock_ehr.get_care_plans(db, patient_id)

    # --- Write ---

    async def create_communication(self, db: AsyncSession, patient_id: uuid.UUID, data: CommunicationCreate, tenant: TenantContext):
        hospital_id = await self._verify_patient_access(db, patient_id, tenant)
        comm = await mock_ehr.create_communication(db, hospital_id, patient_id, data)
        await audit_service.log_event(db, "EHR_COMMUNICATION_CREATED", tenant.user_id, hospital_id, "PATIENT", patient_id)
        return comm

    async def create_task(self, db: AsyncSession, patient_id: uuid.UUID, data: TaskCreate, tenant: TenantContext):
        hospital_id = await self._verify_patient_access(db, patient_id, tenant)
        task = await mock_ehr.create_task(db, hospital_id, patient_id, data)
        action = "EHR_ESCALATION_CREATED" if data.task_type.lower() == "escalation" else "EHR_TASK_CREATED"
        await audit_service.log_event(db, action, tenant.user_id, hospital_id, "PATIENT", patient_id)
        return task

    async def create_observation(self, db: AsyncSession, patient_id: uuid.UUID, data: ObservationCreate, tenant: TenantContext):
        hospital_id = await self._verify_patient_access(db, patient_id, tenant)
        obs = await mock_ehr.create_observation(db, hospital_id, patient_id, data)
        return obs

    async def update_encounter(self, db: AsyncSession, encounter_id: uuid.UUID, data: EncounterUpdate, tenant: TenantContext):
        hospital_id = await self._verify_encounter_access(db, encounter_id, tenant)
        enc = await mock_ehr.update_encounter(db, encounter_id, data)
        await audit_service.log_event(db, "EHR_RECORD_UPDATED", tenant.user_id, hospital_id, "ENCOUNTER", encounter_id)
        return enc

    async def record_outreach_outcome(self, db: AsyncSession, patient_id: uuid.UUID, data: OutreachOutcomeCreate, tenant: TenantContext):
        hospital_id = await self._verify_patient_access(db, patient_id, tenant)
        
        # In a real system this might update a campaign or specific outcome table,
        # here we'll map it to a communication or observation to keep it simple.
        comm_data = CommunicationCreate(
            communication_type="Outreach Outcome",
            content=f"Status: {data.outcome_status} | Notes: {data.notes or ''}"
        )
        await mock_ehr.create_communication(db, hospital_id, patient_id, comm_data)
        await audit_service.log_event(db, "EHR_OUTREACH_OUTCOME_RECORDED", tenant.user_id, hospital_id, "PATIENT", patient_id)
        return {"status": "success", "recorded": True}


    # --- Simulated Data ---

    async def generate_simulated_discharges(self, db: AsyncSession, hospital_id: uuid.UUID, count: int, tenant: TenantContext):
        """Generates mock patients and related discharges for the given hospital."""
        if hospital_id and not tenant.can_access_hospital(hospital_id):
            raise HTTPException(status_code=403, detail="Access denied")

        first_names = [
            "John", "Jane", "Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Heidi",
            "Ivan", "Judy", "Mallory", "Niaj", "Olivia", "Peggy", "Rupert", "Sybil", "Trent", "Victor",
            "Walter", "David", "Mary", "James", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
            "William", "Elizabeth", "Barbara", "Richard", "Susan", "Joseph", "Jessica", "Thomas",
            "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa", "Matthew", "Betty",
            "Anthony", "Margaret", "Mark", "Sandra", "Donald", "Ashley", "Steven", "Kimberly",
            "Paul", "Emily", "Andrew", "Donna", "Joshua", "Michelle", "Kenneth", "Dorothy",
            "Kevin", "Carol", "Brian", "Amanda", "George", "Melissa", "Edward", "Deborah",
            "Ronald", "Stephanie", "Timothy", "Rebecca", "Jason", "Sharon", "Jeffrey", "Laura",
            "Ryan", "Cynthia", "Jacob", "Kathleen", "Gary", "Amy", "Nicholas", "Shirley",
            "Eric", "Angela", "Jonathan", "Helen", "Stephen", "Anna", "Larry", "Brenda",
            "Justin", "Pamela", "Scott", "Nicole", "Brandon", "Emma", "Benjamin", "Samantha"
        ]
        last_names = [
            "Smith", "Doe", "Johnson", "Brown", "Williams", "Jones", "Miller", "Davis",
            "Garcia", "Rodriguez", "Wilson", "Martinez", "Anderson", "Taylor", "Thomas", "Hernandez",
            "Moore", "Martin", "Jackson", "Thompson", "White", "Lopez", "Lee", "Gonzalez",
            "Harris", "Clark", "Lewis", "Robinson", "Walker", "Perez", "Hall", "Young",
            "Allen", "Sanchez", "Wright", "King", "Scott", "Green", "Baker", "Adams",
            "Nelson", "Hill", "Ramirez", "Campbell", "Mitchell", "Roberts", "Carter", "Phillips",
            "Evans", "Turner", "Torres", "Parker", "Collins", "Edwards", "Stewart", "Flores",
            "Morris", "Nguyen", "Murphy", "Rivera", "Cook", "Rogers", "Morgan", "Peterson",
            "Cooper", "Reed", "Bailey", "Bell", "Gomez", "Kelly", "Howard", "Ward", "Cox",
            "Diaz", "Richardson", "Wood", "Watson", "Brooks", "Bennett", "Gray", "James",
            "Reyes", "Cruz", "Hughes", "Price", "Myers", "Long", "Foster", "Sanders", "Ross",
            "Morales", "Powell", "Sullivan", "Russell", "Ortiz", "Jenkins", "Gutierrez", "Perry"
        ]

        scenarios = [
            {
                "name": "Heart Failure",
                "primary": ("I50.9", "Heart failure, unspecified"),
                "base_risk": "High",
                "age_weights": [(18, 30, 0), (31, 50, 5), (51, 70, 35), (71, 95, 60)],
                "comorbidities": [("I10", "Essential (primary) hypertension"), ("N18.9", "Chronic kidney disease, unspecified"), ("I25.10", "Atherosclerotic heart disease of native coronary artery without angina pectoris"), ("E11.9", "Type 2 diabetes mellitus without complications")],
                "medications": [("Furosemide", "40mg", "PO", "Daily"), ("Lisinopril", "10mg", "PO", "Daily"), ("Metoprolol", "25mg", "PO", "BID"), ("Spironolactone", "25mg", "PO", "Daily")],
                "observations": ["bp", "hr", "weight", "spo2"],
                "instructions": "Monitor daily weight. Follow low-sodium diet. Take medications as prescribed. Monitor swelling or shortness of breath. Follow up with cardiology/primary care.",
                "care_plan": "Heart Failure Management Plan",
                "probability": 10
            },
            {
                "name": "Type 2 Diabetes",
                "primary": ("E11.9", "Type 2 diabetes mellitus without complications"),
                "base_risk": "Medium",
                "age_weights": [(18, 30, 5), (31, 50, 25), (51, 70, 45), (71, 95, 25)],
                "comorbidities": [("I10", "Essential (primary) hypertension"), ("E78.5", "Hyperlipidemia, unspecified"), ("N18.9", "Chronic kidney disease, unspecified"), ("E66.9", "Obesity, unspecified")],
                "medications": [("Metformin", "500mg", "PO", "BID"), ("Insulin Glargine", "10 units", "SubQ", "Nightly"), ("Glipizide", "5mg", "PO", "Daily")],
                "observations": ["glucose", "bp", "weight"],
                "instructions": "Monitor blood glucose. Follow medication instructions. Maintain diet plan. Schedule follow-up.",
                "care_plan": "Diabetes Management Plan",
                "probability": 10
            },
            {
                "name": "COPD",
                "primary": ("J44.9", "Chronic obstructive pulmonary disease, unspecified"),
                "base_risk": "Medium",
                "age_weights": [(18, 30, 0), (31, 50, 10), (51, 70, 50), (71, 95, 40)],
                "comorbidities": [("I10", "Essential (primary) hypertension"), ("J18.9", "Pneumonia, unspecified organism"), ("E11.9", "Type 2 diabetes mellitus without complications")],
                "medications": [("Albuterol", "90mcg", "Inhalation", "PRN"), ("Fluticasone", "250mcg", "Inhalation", "BID"), ("Tiotropium", "18mcg", "Inhalation", "Daily")],
                "observations": ["spo2", "rr", "hr"],
                "instructions": "Use inhaler correctly. Monitor breathing. Avoid respiratory triggers. Seek care if breathing worsens.",
                "care_plan": "COPD Recovery Plan",
                "probability": 10
            },
            {
                "name": "Hypertension",
                "primary": ("I10", "Essential (primary) hypertension"),
                "base_risk": "Low",
                "age_weights": [(18, 30, 5), (31, 50, 30), (51, 70, 45), (71, 95, 20)],
                "comorbidities": [("E78.5", "Hyperlipidemia, unspecified"), ("E66.9", "Obesity, unspecified")],
                "medications": [("Amlodipine", "5mg", "PO", "Daily"), ("Losartan", "50mg", "PO", "Daily"), ("Lisinopril", "10mg", "PO", "Daily")],
                "observations": ["bp", "hr"],
                "instructions": "Monitor blood pressure regularly. Maintain a low-sodium diet. Take medications as prescribed.",
                "care_plan": "Hypertension Follow-up Plan",
                "probability": 15
            },
            {
                "name": "Pneumonia",
                "primary": ("J18.9", "Pneumonia, unspecified organism"),
                "base_risk": "Medium",
                "age_weights": [(18, 30, 15), (31, 50, 20), (51, 70, 30), (71, 95, 35)],
                "comorbidities": [("J44.9", "Chronic obstructive pulmonary disease, unspecified"), ("I10", "Essential (primary) hypertension")],
                "medications": [("Amoxicillin", "500mg", "PO", "TID"), ("Azithromycin", "500mg", "PO", "Daily"), ("Acetaminophen", "500mg", "PO", "PRN")],
                "observations": ["temp", "spo2", "rr"],
                "instructions": "Complete the full course of antibiotics. Rest and drink plenty of fluids. Return if symptoms worsen.",
                "care_plan": "Pneumonia Recovery Plan",
                "probability": 6
            },
            {
                "name": "Atrial Fibrillation",
                "primary": ("I48.91", "Unspecified atrial fibrillation"),
                "base_risk": "High",
                "age_weights": [(18, 30, 0), (31, 50, 5), (51, 70, 40), (71, 95, 55)],
                "comorbidities": [("I10", "Essential (primary) hypertension"), ("I50.9", "Heart failure, unspecified")],
                "medications": [("Apixaban", "5mg", "PO", "BID"), ("Metoprolol", "25mg", "PO", "BID"), ("Diltiazem", "120mg", "PO", "Daily")],
                "observations": ["hr", "bp"],
                "instructions": "Take anticoagulants exactly as prescribed. Monitor for signs of bleeding. Keep follow-up appointments.",
                "care_plan": "Atrial Fibrillation Monitoring Plan",
                "probability": 6
            },
            {
                "name": "Coronary Artery Disease",
                "primary": ("I25.10", "Atherosclerotic heart disease of native coronary artery without angina pectoris"),
                "base_risk": "High",
                "age_weights": [(18, 30, 0), (31, 50, 15), (51, 70, 50), (71, 95, 35)],
                "comorbidities": [("E78.5", "Hyperlipidemia, unspecified"), ("I10", "Essential (primary) hypertension"), ("E11.9", "Type 2 diabetes mellitus without complications")],
                "medications": [("Atorvastatin", "40mg", "PO", "Daily"), ("Aspirin", "81mg", "PO", "Daily"), ("Metoprolol", "25mg", "PO", "BID")],
                "observations": ["bp", "hr"],
                "instructions": "Maintain heart-healthy diet. Take aspirin and statins as prescribed. Report any chest pain immediately.",
                "care_plan": "CAD Management Plan",
                "probability": 7
            },
            {
                "name": "Chronic Kidney Disease",
                "primary": ("N18.9", "Chronic kidney disease, unspecified"),
                "base_risk": "High",
                "age_weights": [(18, 30, 0), (31, 50, 10), (51, 70, 40), (71, 95, 50)],
                "comorbidities": [("I10", "Essential (primary) hypertension"), ("E11.9", "Type 2 diabetes mellitus without complications"), ("D64.9", "Anemia, unspecified")],
                "medications": [("Lisinopril", "10mg", "PO", "Daily"), ("Furosemide", "20mg", "PO", "Daily")],
                "observations": ["bp", "weight"],
                "instructions": "Follow renal diet strictly. Avoid NSAIDs. Attend all scheduled lab appointments.",
                "care_plan": "CKD Monitoring Plan",
                "probability": 5
            },
            {
                "name": "Asthma",
                "primary": ("J45.909", "Unspecified asthma, uncomplicated"),
                "base_risk": "Low",
                "age_weights": [(18, 30, 40), (31, 50, 40), (51, 70, 15), (71, 95, 5)],
                "comorbidities": [("J30.9", "Allergic rhinitis, unspecified")],
                "medications": [("Albuterol", "90mcg", "Inhalation", "PRN"), ("Budesonide", "180mcg", "Inhalation", "BID")],
                "observations": ["spo2", "rr"],
                "instructions": "Use preventer inhaler daily. Keep rescue inhaler available at all times. Avoid known triggers.",
                "care_plan": "Asthma Action Plan",
                "probability": 7
            },
            {
                "name": "Post-Surgical Recovery",
                "primary": ("Z98.890", "Other specified postprocedural states"),
                "base_risk": "Medium",
                "age_weights": [(18, 30, 10), (31, 50, 30), (51, 70, 40), (71, 95, 20)],
                "comorbidities": [("I10", "Essential (primary) hypertension")],
                "medications": [("Oxycodone", "5mg", "PO", "PRN"), ("Ibuprofen", "600mg", "PO", "Q8H"), ("Cephalexin", "500mg", "PO", "QID")],
                "observations": ["temp", "bp", "hr"],
                "instructions": "Keep surgical site clean and dry. Monitor for signs of infection. Manage pain as prescribed.",
                "care_plan": "Post-Surgical Recovery Plan",
                "probability": 7
            },
            {
                "name": "Infection",
                "primary": ("A41.9", "Sepsis, unspecified organism"),
                "base_risk": "High",
                "age_weights": [(18, 30, 10), (31, 50, 20), (51, 70, 30), (71, 95, 40)],
                "comorbidities": [("E11.9", "Type 2 diabetes mellitus without complications")],
                "medications": [("Ceftriaxone", "1g", "IV", "Daily"), ("Vancomycin", "1g", "IV", "BID"), ("Acetaminophen", "500mg", "PO", "PRN")],
                "observations": ["temp", "bp", "hr", "rr", "spo2"],
                "instructions": "Complete all antibiotics. Monitor for fever. Return immediately if symptoms return or worsen.",
                "care_plan": "Severe Infection Recovery Plan",
                "probability": 3
            },
            {
                "name": "Anemia",
                "primary": ("D64.9", "Anemia, unspecified"),
                "base_risk": "Low",
                "age_weights": [(18, 30, 20), (31, 50, 20), (51, 70, 30), (71, 95, 30)],
                "comorbidities": [("N18.9", "Chronic kidney disease, unspecified")],
                "medications": [("Ferrous Sulfate", "325mg", "PO", "Daily")],
                "observations": ["hr", "bp"],
                "instructions": "Take iron supplements with vitamin C. Monitor for dark stools. Follow up for repeat bloodwork.",
                "care_plan": "Anemia Follow-up Plan",
                "probability": 4
            },
            {
                "name": "Hyperlipidemia",
                "primary": ("E78.5", "Hyperlipidemia, unspecified"),
                "base_risk": "Low",
                "age_weights": [(18, 30, 5), (31, 50, 35), (51, 70, 45), (71, 95, 15)],
                "comorbidities": [("I10", "Essential (primary) hypertension")],
                "medications": [("Atorvastatin", "40mg", "PO", "Daily"), ("Rosuvastatin", "20mg", "PO", "Daily")],
                "observations": ["bp", "weight"],
                "instructions": "Follow a low-cholesterol diet. Exercise regularly. Take statins daily as prescribed.",
                "care_plan": "Lipid Management Plan",
                "probability": 5
            },
            {
                "name": "General Low-Risk Routine Discharge",
                "primary": ("Z13.89", "Encounter for screening for other disorder"),
                "base_risk": "Low",
                "age_weights": [(18, 30, 40), (31, 50, 40), (51, 70, 15), (71, 95, 5)],
                "comorbidities": [],
                "medications": [("Acetaminophen", "500mg", "PO", "PRN"), ("Ibuprofen", "400mg", "PO", "PRN")],
                "observations": ["bp", "temp"],
                "instructions": "Routine discharge. Follow up with primary care physician as needed. Maintain healthy lifestyle.",
                "care_plan": "Routine Follow-up Plan",
                "probability": 5
            }
        ]

        provided_hospitals = [
            uuid.UUID("9dde708b-d55c-49f7-99e3-59c3e03101e1"),
            uuid.UUID("79d10cab-224b-49dd-b4f0-a79d14b148c5"),
            uuid.UUID("a9cf4331-84d6-4f93-8233-c40d30f22bf3"),
            uuid.UUID("00bf8d38-5100-4a94-b04f-0441e3284682"),
            uuid.UUID("8f917625-fd01-4782-9de6-338d71b2ba36"),
            uuid.UUID("cdb58af3-9b82-4bc6-ae6d-7e5d453f8775"),
            uuid.UUID("9e77cf2e-e6a9-4be7-8fbd-30aaf407a19c"),
            uuid.UUID("d3bfe861-51c6-4aad-8c41-493aee3a238d"),
            uuid.UUID("20bcc8a6-05fb-422b-9c09-e56330128cc8"),
            uuid.UUID("a45388ed-6938-4f4a-99fc-1710a0de839f"),
            uuid.UUID("ef21c2e4-49e3-498e-80f0-813d0dba6d1c"),
            uuid.UUID("adf53a33-74a4-486d-b883-5a9ef546d81d")
        ]
        
        # Enforce tenant isolation if not platform admin
        if not tenant.is_platform_admin:
            if tenant.hospital_id in provided_hospitals:
                provided_hospitals = [tenant.hospital_id]
            else:
                provided_hospitals = [hospital_id]

        hospital_counts = {}
        for h_id in provided_hospitals:
            res = await db.execute(select(Patient.id).where(Patient.hospital_id == h_id, Patient.external_patient_id.like(f"MOCK-{h_id}-%")))
            hospital_counts[h_id] = len(res.scalars().all())

        counts = {
            "patients": 0, "encounters": 0, "discharges": 0, "conditions": 0,
            "medications": 0, "observations": 0, "care_plans": 0
        }
        risks = {"Low": 0, "Medium": 0, "High": 0}
        
        clinical_distribution = {s["name"]: 0 for s in scenarios}
        campaign_segments = {
            "High risk": 0, "Medium risk": 0, "Low risk": 0,
            "Heart failure patients": 0, "Diabetes patients": 0, "COPD patients": 0, "Hypertension patients": 0,
            "Discharged last 48 hours": 0, "Discharged last 7 days": 0,
            "Follow-up required": 0, "Follow-up due soon (<= 48h)": 0,
            "Abnormal observations": 0,
            "3+ medications": 0, "3+ conditions": 0,
            "ICU discharges": 0, "Elderly patients (65+)": 0,
            "Prefers phone": 0, "Prefers sms": 0, "Prefers email": 0
        }
        
        representative_patients = []
        
        scenario_weights = [s["probability"] for s in scenarios]

        try:
            for i in range(count):
                assigned_hospital_id = random.choice(provided_hospitals)
                patient_index = hospital_counts[assigned_hospital_id]
                hospital_counts[assigned_hospital_id] += 1
                
                ext_patient_id = f"MOCK-{assigned_hospital_id}-{patient_index}"
                ext_encounter_id = f"MOCK-ENC-{assigned_hospital_id}-{patient_index}"
                
                # Pick Scenario
                scenario = random.choices(scenarios, weights=scenario_weights)[0]
                clinical_distribution[scenario["name"]] += 1
                
                # Demographics
                age_bracket = random.choices(scenario["age_weights"], weights=[w[2] for w in scenario["age_weights"]])[0]
                birth_year = datetime.utcnow().year - random.randint(age_bracket[0], age_bracket[1])
                dob = date(birth_year, random.randint(1, 12), random.randint(1, 28))
                age_years = datetime.utcnow().year - birth_year
                
                contact_method = random.choice(["phone", "sms", "email"])
                if contact_method == "phone": campaign_segments["Prefers phone"] += 1
                elif contact_method == "sms": campaign_segments["Prefers sms"] += 1
                elif contact_method == "email": campaign_segments["Prefers email"] += 1
                
                if age_years >= 65:
                    campaign_segments["Elderly patients (65+)"] += 1

                p = Patient(
                    hospital_id=assigned_hospital_id,
                    external_patient_id=ext_patient_id,
                    first_name=random.choice(first_names),
                    last_name=random.choice(last_names),
                    gender=random.choice(["male", "female", "other"]),
                    date_of_birth=dob,
                    phone=f"555-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
                    email=f"{random.randint(1000,9999)}@example.com",
                    preferred_contact_method=contact_method
                )
                db.add(p)
                await db.flush()
                counts["patients"] += 1
                
                # Comorbidities & Risk Calculation
                num_comorbidities = random.choices([0, 1, 2], weights=[40, 40, 20])[0]
                if not scenario["comorbidities"]: num_comorbidities = 0
                chosen_comorbidities = random.sample(scenario["comorbidities"], min(num_comorbidities, len(scenario["comorbidities"])))
                total_conditions = 1 + len(chosen_comorbidities)
                
                if total_conditions >= 3:
                    campaign_segments["3+ conditions"] += 1
                
                if scenario["name"] == "Heart Failure": campaign_segments["Heart failure patients"] += 1
                if scenario["name"] == "Type 2 Diabetes": campaign_segments["Diabetes patients"] += 1
                if scenario["name"] == "COPD": campaign_segments["COPD patients"] += 1
                if scenario["name"] == "Hypertension": campaign_segments["Hypertension patients"] += 1
                
                # Determine risk based on base risk + modifiers
                risk_val = {"Low": 1, "Medium": 2, "High": 3}[scenario["base_risk"]]
                if age_years >= 70: risk_val += 1
                if total_conditions >= 3: risk_val += 1
                
                # Target distribution scaling (roughly mapping back to Low/Medium/High)
                if risk_val >= 4: risk = "High"
                elif risk_val == 3: risk = random.choice(["Medium", "High"])
                elif risk_val == 2: risk = "Medium"
                else: risk = "Low"
                
                risks[risk] += 1
                campaign_segments[f"{risk} risk"] += 1

                # Encounter Dates & Settings
                adm_time = datetime.utcnow() - timedelta(days=random.randint(2, 20))
                days_ago = random.uniform(0, 7)
                dis_time = datetime.utcnow() - timedelta(days=days_ago)
                if dis_time < adm_time: adm_time = dis_time - timedelta(days=random.randint(1, 10))
                
                if days_ago <= 2: campaign_segments["Discharged last 48 hours"] += 1
                campaign_segments["Discharged last 7 days"] += 1
                
                if risk == "High": care_setting = random.choice(["icu", "step_down"])
                elif risk == "Medium": care_setting = random.choice(["general_ward", "step_down", "medical"])
                else: care_setting = random.choice(["general_ward", "observation"])
                
                if care_setting == "icu": campaign_segments["ICU discharges"] += 1

                e = Encounter(
                    hospital_id=assigned_hospital_id,
                    patient_id=p.id,
                    external_encounter_id=ext_encounter_id,
                    encounter_type=random.choice(["inpatient", "emergency", "observation"]),
                    care_setting=care_setting,
                    admission_time=adm_time,
                    discharge_time=dis_time,
                    status="finished"
                )
                db.add(e)
                await db.flush()
                counts["encounters"] += 1

                # Follow-up rules
                fu_required = (risk in ["Medium", "High"])
                if fu_required: campaign_segments["Follow-up required"] += 1
                
                if risk == "High": fu_deadline = dis_time + timedelta(days=random.randint(1, 3))
                elif risk == "Medium": fu_deadline = dis_time + timedelta(days=random.randint(3, 7))
                else: fu_deadline = dis_time + timedelta(days=random.randint(7, 14)) if random.random() < 0.3 else None
                
                if fu_deadline and fu_deadline <= datetime.utcnow() + timedelta(days=2):
                    campaign_segments["Follow-up due soon (<= 48h)"] += 1

                d = Discharge(
                    hospital_id=assigned_hospital_id,
                    patient_id=p.id,
                    encounter_id=e.id,
                    discharge_timestamp=dis_time,
                    discharge_status="home",
                    discharge_instructions=scenario["instructions"],
                    follow_up_required=fu_required,
                    follow_up_start=dis_time,
                    follow_up_deadline=fu_deadline,
                    risk_level=risk,
                    risk_indicators=[{"reason": "Clinical profile evaluation"}]
                )
                db.add(d)
                counts["discharges"] += 1

                # Add Conditions
                conds = [scenario["primary"]] + chosen_comorbidities
                for cd in conds:
                    c = Condition(
                        hospital_id=assigned_hospital_id,
                        patient_id=p.id,
                        encounter_id=e.id,
                        code=cd[0],
                        display=cd[1],
                        clinical_status="active",
                        onset_date=adm_time - timedelta(days=random.randint(10, 365))
                    )
                    db.add(c)
                    counts["conditions"] += 1
                
                # Add Medications
                meds_count = random.randint(1, len(scenario["medications"]))
                if meds_count >= 3: campaign_segments["3+ medications"] += 1
                
                patient_meds = random.sample(scenario["medications"], meds_count)
                for m_data in patient_meds:
                    m = Medication(
                        hospital_id=assigned_hospital_id,
                        patient_id=p.id,
                        encounter_id=e.id,
                        name=m_data[0],
                        dosage=m_data[1],
                        route=m_data[2],
                        frequency=m_data[3],
                        status="active",
                        start_date=adm_time,
                        end_date=dis_time + timedelta(days=30)
                    )
                    db.add(m)
                    counts["medications"] += 1

                # Care Plan
                if risk in ["Medium", "High"]:
                    cp = CarePlan(
                        hospital_id=assigned_hospital_id,
                        patient_id=p.id,
                        encounter_id=e.id,
                        title=scenario["care_plan"],
                        description=f"Personalized care plan for {scenario['name']}",
                        status="active",
                        start_date=dis_time,
                        end_date=dis_time + timedelta(days=90)
                    )
                    db.add(cp)
                    counts["care_plans"] += 1

                # Observations
                abnormal = False
                obs_to_generate = random.sample(scenario["observations"], random.randint(min(2, len(scenario["observations"])), len(scenario["observations"])))
                
                def get_obs_val(type_, rsk):
                    if type_ == "bp": return ("8480-6", "Systolic blood pressure", "mmHg", random.randint(100, 130) if rsk == "Low" else (random.randint(130, 150) if rsk == "Medium" else random.randint(140, 180)))
                    if type_ == "hr": return ("8867-4", "Heart rate", "beats/min", random.randint(60, 90) if rsk == "Low" else (random.randint(85, 105) if rsk == "Medium" else random.randint(100, 130)))
                    if type_ == "weight": return ("29463-7", "Body weight", "kg", round(random.uniform(60.0, 90.0), 1))
                    if type_ == "spo2": return ("2708-6", "Oxygen saturation", "%", random.randint(95, 100) if rsk == "Low" else (random.randint(92, 95) if rsk == "Medium" else random.randint(88, 93)))
                    if type_ == "glucose": return ("15074-8", "Glucose", "mg/dL", random.randint(80, 120) if rsk == "Low" else (random.randint(120, 180) if rsk == "Medium" else random.randint(180, 300)))
                    if type_ == "temp": return ("8310-5", "Body temperature", "Cel", round(random.uniform(36.5, 37.2), 1) if rsk == "Low" else (round(random.uniform(37.3, 38.0), 1) if rsk == "Medium" else round(random.uniform(38.1, 39.5), 1)))
                    if type_ == "rr": return ("9279-1", "Respiratory rate", "breaths/min", random.randint(12, 18) if rsk == "Low" else (random.randint(18, 22) if rsk == "Medium" else random.randint(22, 30)))

                patient_obs = []
                for obs_key in obs_to_generate:
                    code, disp, unit, val = get_obs_val(obs_key, risk)
                    
                    # Very simple abnormality check for the segment
                    if (obs_key == "bp" and val > 140) or (obs_key == "spo2" and val < 94) or (obs_key == "temp" and val > 37.8) or (obs_key == "glucose" and val > 140):
                        abnormal = True

                    obs = Observation(
                        hospital_id=assigned_hospital_id,
                        patient_id=p.id,
                        encounter_id=e.id,
                        code=code,
                        display=disp,
                        value=str(val),
                        unit=unit,
                        status="final",
                        observed_at=dis_time - timedelta(hours=random.randint(1, 48))
                    )
                    db.add(obs)
                    counts["observations"] += 1
                    patient_obs.append(f"{disp}: {val} {unit}")
                    
                if abnormal:
                    campaign_segments["Abnormal observations"] += 1

                # Save representative profiles
                if len(representative_patients) < 5 and (i % max(1, count // 5) == 0):
                    representative_patients.append({
                        "Age": age_years,
                        "Primary Condition": scenario["name"],
                        "Risk Level": risk,
                        "Care Setting": care_setting,
                        "Medications Count": meds_count,
                        "Follow Up Required": fu_required,
                        "Sample Observations": patient_obs[:2]
                    })

            await db.commit()
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to generate mock data: {str(e)}")

        for h_id in provided_hospitals:
            if hospital_counts[h_id] > 0:
                await audit_service.log_event(
                    db, 
                    "PATIENT_IMPORTED", 
                    tenant.user_id, 
                    h_id, 
                    "HOSPITAL", 
                    h_id, 
                    metadata={"count": hospital_counts[h_id], "resource_counts": counts}
                )
        
        return {
            "imported_count": count,
            "resource_counts": counts,
            "risk_distribution": risks,
            "patients_per_hospital": {str(k): v for k, v in hospital_counts.items() if v > 0},
            "averages": {
                "conditions_per_patient": round(counts["conditions"] / count, 1) if count > 0 else 0,
                "medications_per_patient": round(counts["medications"] / count, 1) if count > 0 else 0,
                "observations_per_patient": round(counts["observations"] / count, 1) if count > 0 else 0,
            },
            "clinical_distribution": clinical_distribution,
            "campaign_ready_segments": campaign_segments,
            "representative_patients": representative_patients
        }

healthcare_data_service = HealthcareDataService()
