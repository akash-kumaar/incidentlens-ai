// API types matching backend Pydantic models

export type Severity = 'info' | 'warning' | 'high' | 'critical';
export type InvestigationStatus =
  | 'pending' | 'running' | 'collecting_evidence' | 'analyzing'
  | 'awaiting_approval' | 'remediating' | 'verifying' | 'completed' | 'failed';
export type ToolStatus = 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
export type RemediationStatus =
  | 'proposed' | 'awaiting_approval' | 'approved' | 'executing'
  | 'completed' | 'rejected' | 'failed';
export type ConfidenceCategory =
  | 'strongly_supported' | 'plausible' | 'weakly_supported' | 'insufficient_evidence';

export interface Scenario {
  id: string;
  name: string;
  description: string;
  service: string;
  severity: Severity;
  tags: string[];
}

export interface Service {
  id: string;
  name: string;
  description: string;
  team: string;
  environment: string;
  language: string;
  framework: string;
}

export interface EvidenceItem {
  id: string;
  timestamp: string;
  source: string;
  service: string;
  severity: string;
  evidence_type: string;
  summary: string;
  detail: string;
  relevance: 'supporting' | 'contradictory' | 'neutral';
  raw?: Record<string, unknown>;
}

export interface ToolExecution {
  tool_name: string;
  display_name: string;
  description: string;
  status: ToolStatus;
  started_at?: string;
  completed_at?: string;
  result_summary?: string;
  error?: string;
  evidence_count: number;
}

export interface Hypothesis {
  id: string;
  title: string;
  rank: number;
  confidence: ConfidenceCategory;
  confidence_explanation: string;
  supporting_evidence: string[];
  contradictory_evidence: string[];
  missing_evidence: string[];
  recommended_verification: string;
  recommended_action: string;
}

export interface RemediationProposal {
  action_id: string;
  action_type: string;
  title: string;
  description: string;
  reason: string;
  expected_outcome: string;
  risks: string[];
  what_will_change: string;
  verification_procedure: string;
  status: RemediationStatus;
  approved_at?: string;
  executed_at?: string;
}

export interface RemediationResult {
  action_id: string;
  status: string;
  changes_applied: string[];
  timestamp: string;
  environment: string;
}

export interface VerificationCheck {
  check: string;
  before: string;
  after: string;
  passed: boolean;
}

export interface VerificationResult {
  checks: VerificationCheck[];
  before_metrics: Record<string, number>;
  after_metrics: Record<string, number>;
  passed: boolean;
  remaining_issues: string[];
  final_status: string;
}

export interface TimelineEvent {
  timestamp: string;
  type: string;
  title: string;
  description: string;
  severity: string;
}

export interface PostmortemReport {
  incident_id: string;
  service: string;
  severity: string;
  start_time: string;
  end_time?: string;
  impact_summary: string;
  final_status: string;
  timeline: TimelineEvent[];
  root_cause_assessment: string;
  contributing_factors: string[];
  resolution: string;
  what_went_well: string[];
  what_could_improve: string[];
  follow_up_actions: Array<{ action: string; priority: string; rationale: string }>;
  unresolved_questions: string[];
  generated_at: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export interface Investigation {
  id: string;
  incident_description: string;
  service: string;
  scenario_id: string;
  depth: string;
  status: InvestigationStatus;
  progress: number;
  tool_history: ToolExecution[];
  evidence: EvidenceItem[];
  hypotheses: Hypothesis[];
  remediation?: RemediationProposal;
  remediation_result?: RemediationResult;
  verification_result?: VerificationResult;
  report?: PostmortemReport;
  ai_provider_used: string;
  created_at: string;
  updated_at: string;
  completed_at?: string;
  error?: string;
  chat_messages: ChatMessage[];
}

export interface ProviderStatus {
  provider: string;
  bedrock_configured: boolean;
  bedrock_region?: string;
  bedrock_model?: string;
  bedrock_status: string;
  s3_configured: boolean;
  s3_bucket?: string;
  s3_status: string;
  demo_mode: boolean;
  version: string;
}
