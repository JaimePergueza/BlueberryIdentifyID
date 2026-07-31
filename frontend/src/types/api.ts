export type UserRole = "admin" | "specialist";

export interface User {
  id: string;
  username: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: "bearer";
  expires_at: string;
  user: User;
}

export type AnalysisStatus =
  | "pending"
  | "processing"
  | "completed"
  | "needs_review"
  | "failed";

export type PredictedLabel =
  | "no_evident_growth"
  | "suspicious_growth"
  | "probable_fungal_growth"
  | "probable_bacterial_growth"
  | "inconclusive";

export type ReviewDecision =
  | "confirmed"
  | "corrected"
  | "marked_inconclusive"
  | "rejected_invalid_sample";

export interface AnalysisHistoryItem {
  analysis_run_id: string;
  sample_id: string;
  sample_code: string;
  petri_image_id: string;
  micro_image_id: string;
  model_version_id: string;
  model_name: string;
  model_version: string;
  model_type: string;
  analysis_status: AnalysisStatus;
  created_at: string;
  completed_at: string | null;
  preliminary_label: PredictedLabel | null;
  confidence_score: number | null;
  requires_human_review: boolean;
  review_status: "pending" | "reviewed";
  final_review_id: string | null;
  review_decision: ReviewDecision | null;
  reviewer_name: string | null;
  reviewed_at: string | null;
  final_label: PredictedLabel | null;
  final_status: string;
}

export interface AnalysisHistoryPage {
  items: AnalysisHistoryItem[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface UploadAnalysisResponse {
  analysis_run_id: string;
  prediction_id: string;
  sample_id: string;
  petri_image_id: string;
  micro_image_id: string;
  predicted_label: PredictedLabel;
  confidence_score: number | null;
  class_probabilities: Record<string, number>;
  requires_human_review: true;
  disclaimer: string;
  explanation: string | null;
  feature_summary: Record<string, unknown> | null;
  quality_summary: Record<string, unknown> | null;
  decision_trace: unknown[] | null;
  warnings: string[] | null;
}

export interface PreliminaryResult {
  analysis_run_id: string;
  prediction_id: string;
  sample_id: string;
  predicted_label: PredictedLabel;
  confidence_score: number | null;
  class_probabilities: Record<string, number>;
  requires_human_review: boolean;
  technical_observation: string | null;
  disclaimer: string;
  explanation: string | null;
  feature_summary: Record<string, unknown> | null;
  quality_summary: Record<string, unknown> | null;
  decision_trace: unknown[] | null;
  warnings: string[] | null;
  human_review_status: string | null;
  human_review_completed: boolean;
  latest_human_review_id: string | null;
  latest_human_review_decision: ReviewDecision | null;
  final_label: PredictedLabel | null;
  reviewed_at: string | null;
}

export interface HumanReview {
  id: string;
  analysis_run_id: string;
  reviewer_name: string;
  review_decision: ReviewDecision;
  corrected_label: PredictedLabel | null;
  comments: string | null;
  is_final: boolean;
  created_at: string;
}

export interface AnalysisDetail {
  analysis_run: {
    id: string;
    status: AnalysisStatus;
    created_at: string;
    started_at: string | null;
    completed_at: string | null;
    error_message: string | null;
  };
  sample: {
    id: string;
    sample_code: string;
    product: string;
    lot_code: string | null;
    origin: string | null;
    collection_date: string | null;
    notes: string | null;
    created_at: string;
  };
  petri_image: ImageMetadata & {
    culture_medium: string | null;
    incubation_temperature_c: number | null;
    incubation_time_hours: number | null;
    seeding_date: string | null;
    observed_colony_color: string | null;
    observed_colony_shape: string | null;
    observed_colony_margin: string | null;
    observed_colony_texture: string | null;
    notes: string | null;
  };
  micro_image: ImageMetadata & {
    magnification: string | null;
    microscope_type: string | null;
    staining_method: string | null;
    preparation_method: string | null;
    observed_structures: string | null;
    notes: string | null;
  };
  model_version: {
    id: string;
    name: string;
    version: string;
    model_type: string;
    description: string | null;
  };
  prediction: null | {
    id: string;
    predicted_label: PredictedLabel;
    confidence_score: number | null;
    class_probabilities: Record<string, number> | null;
    technical_observation: string | null;
    requires_human_review: boolean;
    explanation: string | null;
    feature_summary: Record<string, unknown> | null;
    quality_summary: Record<string, unknown> | null;
    decision_trace: unknown[] | null;
    warnings: string[] | null;
    created_at: string;
  };
  human_review: HumanReview | null;
  final_label: PredictedLabel | null;
  final_status: string;
  human_review_completed: boolean;
  requires_human_review: boolean;
}

interface ImageMetadata {
  id: string;
  file_name: string;
  mime_type: string;
  file_size_bytes: number;
  width: number | null;
  height: number | null;
  captured_at: string | null;
}

export interface ApiErrorPayload {
  error?: {
    code?: string;
    message?: string;
    request_id?: string;
  };
  detail?: string | Array<{ msg?: string }>;
}
