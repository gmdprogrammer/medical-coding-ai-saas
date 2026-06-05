export interface MedicalCode {
  code: string;
  description: string;
  confidence: number;
  confidence_label: "High" | "Medium" | "Low";
  supporting_evidence: string[];
}

export interface CodingResponse {
  session_id: string;
  clinical_summary: string;
  icd10_codes: MedicalCode[];
  cpt_codes: MedicalCode[];
  explanation: string;
  processing_time_ms: number;
  phi_detected: boolean;
  created_at: string;
}

export interface CodingSession {
  id: string;
  clinical_summary: string;
  icd10_count: number;
  cpt_count: number;
  avg_icd_confidence: number;
  avg_cpt_confidence: number;
  feedback_rating: number | null;
  review_status: string;
  created_at: string;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  organization: string | null;
  role: "coder" | "admin" | "reviewer";
  is_active: boolean;
  is_verified: boolean;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface DashboardStats {
  total_users: number;
  total_sessions: number;
  sessions_today: number;
  avg_confidence: number;
  pending_reviews: number;
  accuracy_rate: number;
}

export interface FeedbackRequest {
  session_id: string;
  rating: 1 | 2 | 3 | 4 | 5;
  notes?: string;
  code_corrections?: {
    code_type: "icd10" | "cpt";
    suggested: string;
    correct: string;
    was_correct: boolean;
  }[];
}
