export enum UserRole {
  PLATFORM_ADMIN = "PLATFORM_ADMIN",
  HOSPITAL_ADMIN = "HOSPITAL_ADMIN",
  CAMPAIGN_MANAGER = "CAMPAIGN_MANAGER",
  CLINICAL_REVIEWER = "CLINICAL_REVIEWER",
}

export enum CampaignStatus {
  DRAFT = "DRAFT",
  READY = "READY",
  SCHEDULED = "SCHEDULED",
  RUNNING = "RUNNING",
  PAUSED = "PAUSED",
  COMPLETED = "COMPLETED",
  CANCELLED = "CANCELLED",
  FAILED = "FAILED",
}

export interface User {
  id: string;
  hospital_id: string | null;
  name: string;
  email: string;
  role: UserRole;
  status: string;
  created_at?: string;
  updated_at?: string;
}

export interface Hospital {
  id: string;
  name: string;
  contact_email: string;
  contact_phone: string;
  timezone: string;
  status: string;
  created_at?: string;
  updated_at?: string;
}

export interface Patient {
  id: string;
  hospital_id: string;
  external_patient_id?: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  gender?: string;
  phone: string;
  email?: string;
  preferred_contact_method?: string;
}

export interface Campaign {
  id: string;
  hospital_id: string;
  name: string;
  description?: string;
  status: CampaignStatus;
  validation_status: string;
  eligibility_rules?: Record<string, any>;
  follow_up_window?: Record<string, any>;
  calling_hours?: Record<string, any>;
  priority_config?: Record<string, any>;
  max_retries: number;
  calling_capacity: number;
  start_at?: string;
  end_at?: string;
  created_by?: string;
  protocol_id?: string;
}

export interface TriageResult {
  id: string;
  call_id: string;
  patient_id: string;
  campaign_id: string;
  triage_level: string;
  recommended_action: string;
  requires_human_review: boolean;
  consensus_level: string;
  consensus_method: string;
  disagreement_detected: boolean;
  ehr_action_status: string;
  protocol_name: string;
  created_at: string;
}

export interface TriageDetail extends TriageResult {
  findings: any[];
  red_flags: any[];
  matched_protocol_rules: any[];
  reasoning_summary: string;
  agent_assessments: any[];
}
