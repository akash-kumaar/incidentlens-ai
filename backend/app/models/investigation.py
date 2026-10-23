from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from enum import Enum
import uuid


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"


class InvestigationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COLLECTING_EVIDENCE = "collecting_evidence"
    ANALYZING = "analyzing"
    AWAITING_APPROVAL = "awaiting_approval"
    REMEDIATING = "remediating"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"


class ToolStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class RemediationStatus(str, Enum):
    PROPOSED = "proposed"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    EXECUTING = "executing"
    COMPLETED = "completed"
    REJECTED = "rejected"
    FAILED = "failed"


class ConfidenceCategory(str, Enum):
    STRONGLY_SUPPORTED = "strongly_supported"
    PLAUSIBLE = "plausible"
    WEAKLY_SUPPORTED = "weakly_supported"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


# ─── Evidence ─────────────────────────────────────────────────────────────────

class EvidenceItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: str
    source: str  # tool that produced this
    service: str
    severity: str
    evidence_type: str  # log | metric | deployment | correlation | health
    summary: str
    detail: str
    relevance: str = "supporting"  # supporting | contradictory | neutral
    raw: Optional[Dict[str, Any]] = None


# ─── Tool execution ───────────────────────────────────────────────────────────

class ToolExecution(BaseModel):
    tool_name: str
    display_name: str
    description: str
    status: ToolStatus = ToolStatus.PENDING
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result_summary: Optional[str] = None
    error: Optional[str] = None
    evidence_count: int = 0


# ─── Hypothesis ───────────────────────────────────────────────────────────────

class Hypothesis(BaseModel):
    id: str
    title: str
    rank: int
    confidence: ConfidenceCategory
    confidence_explanation: str
    supporting_evidence: List[str]  # evidence IDs or summaries
    contradictory_evidence: List[str]
    missing_evidence: List[str]
    recommended_verification: str
    recommended_action: str


# ─── Remediation ──────────────────────────────────────────────────────────────

class RemediationProposal(BaseModel):
    action_id: str
    action_type: str
    title: str
    description: str
    reason: str
    expected_outcome: str
    risks: List[str]
    what_will_change: str
    verification_procedure: str
    status: RemediationStatus = RemediationStatus.PROPOSED
    approved_at: Optional[str] = None
    executed_at: Optional[str] = None


class RemediationResult(BaseModel):
    action_id: str
    status: str
    changes_applied: List[str]
    timestamp: str
    environment: str = "SIMULATED"


class VerificationResult(BaseModel):
    checks: List[Dict[str, Any]]
    before_metrics: Dict[str, Any]
    after_metrics: Dict[str, Any]
    passed: bool
    remaining_issues: List[str]
    final_status: str


# ─── Report ───────────────────────────────────────────────────────────────────

class TimelineEvent(BaseModel):
    timestamp: str
    type: str
    title: str
    description: str
    severity: str


class PostmortemReport(BaseModel):
    incident_id: str
    service: str
    severity: str
    start_time: str
    end_time: Optional[str]
    impact_summary: str
    final_status: str
    timeline: List[TimelineEvent]
    root_cause_assessment: str
    contributing_factors: List[str]
    resolution: str
    what_went_well: List[str]
    what_could_improve: List[str]
    follow_up_actions: List[Dict[str, str]]
    unresolved_questions: List[str]
    generated_at: str


# ─── Investigation ────────────────────────────────────────────────────────────

class Investigation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    incident_description: str
    service: str
    scenario_id: str
    depth: str = "standard"  # quick | standard | deep
    status: InvestigationStatus = InvestigationStatus.PENDING
    progress: int = 0  # 0-100
    tool_history: List[ToolExecution] = []
    evidence: List[EvidenceItem] = []
    hypotheses: List[Hypothesis] = []
    remediation: Optional[RemediationProposal] = None
    remediation_result: Optional[RemediationResult] = None
    verification_result: Optional[VerificationResult] = None
    report: Optional[PostmortemReport] = None
    ai_provider_used: str = "local"
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None
    error: Optional[str] = None
    chat_messages: List[Dict[str, str]] = []


# ─── Request / Response models ────────────────────────────────────────────────

class CreateInvestigationRequest(BaseModel):
    incident_description: str
    service: str
    scenario_id: str
    depth: str = "standard"


class ChatRequest(BaseModel):
    message: str
    investigation_id: str


class ApproveRemediationRequest(BaseModel):
    approved: bool


class ProviderStatus(BaseModel):
    provider: str
    bedrock_configured: bool
    bedrock_region: Optional[str]
    bedrock_model: Optional[str]
    bedrock_status: str
    s3_configured: bool
    s3_bucket: Optional[str]
    s3_status: str
    demo_mode: bool
    version: str = "1.0.0"
