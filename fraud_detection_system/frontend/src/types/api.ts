export type InvestigationStatus = 'PENDING' | 'PROCESSING' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED';

export interface Document {
  id: string;
  filename: string;
  file_type: string;
  classification: string | null;
  created_at: string;
}

export interface Evidence {
  id: string;
  finding_id: string;
  document_id: string;
  page_number: number | null;
  coordinates: any | null;
  confidence: number | null;
  extracted_text: string | null;
  description: string | null;
}

export interface Finding {
  id: string;
  investigation_id: string;
  layer_source: string;
  name: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  description: string;
  metadata_json: any | null;
  evidence_items: Evidence[];
}

export interface InvestigationEvent {
  id: string;
  timestamp: string;
  event_type: string;
  message: string;
  metadata_json: any | null;
}

export interface Investigation {
  id: string;
  context: string;
  title: string | null;
  status: InvestigationStatus;
  progress: number;
  current_stage: string;
  trust_score: number | null;
  confidence_score: number | null;
  recommendation: string | null;
  ai_summary_json: any | null;
  is_baseline: boolean;
  created_at: string;
  updated_at: string;
  documents: Document[];
}

export interface InvestigationFull extends Investigation {
  findings: Finding[];
  events: InvestigationEvent[];
}

export interface InvestigationStatusResponse {
  status: InvestigationStatus;
  progress: number;
  current_stage: string;
  message: string | null;
}

export interface InvestigationResult {
  investigation: InvestigationFull;
}
