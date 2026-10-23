"""
FastAPI API routes for IncidentLens AI.
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, Response
from app.models.investigation import (
    CreateInvestigationRequest, ChatRequest, ApproveRemediationRequest,
    Investigation, ProviderStatus, InvestigationStatus,
)
from app.services import incident_engine
from app.services.ai_provider import get_ai_provider, BedrockAIProvider
from app.services.s3_archive import get_s3_status, archive_report
from app.data.scenarios.scenario_data import ALL_SCENARIOS, SERVICES
from app.config import settings

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)


# ── Health ─────────────────────────────────────────────────────────────────────

@router.get("/health")
def health():
    return {"status": "ok", "version": settings.version, "timestamp": datetime.utcnow().isoformat()}


# ── Scenarios & Services ───────────────────────────────────────────────────────

@router.get("/scenarios")
def list_scenarios():
    return [
        {
            "id": s["id"],
            "name": s["name"],
            "description": s["description"],
            "service": s["service"],
            "severity": s["severity"],
            "tags": s["tags"],
        }
        for s in ALL_SCENARIOS.values()
    ]


@router.get("/services")
def list_services():
    return list(SERVICES.values())


# ── Investigations ─────────────────────────────────────────────────────────────

@router.get("/investigations")
def list_investigations():
    investigations = incident_engine.get_all_investigations()
    return sorted([inv.model_dump() for inv in investigations], key=lambda i: i["created_at"], reverse=True)


@router.post("/investigations", status_code=201)
def create_investigation(req: CreateInvestigationRequest):
    if req.scenario_id not in ALL_SCENARIOS:
        raise HTTPException(status_code=400, detail=f"Unknown scenario: {req.scenario_id}")
    if req.service not in SERVICES:
        raise HTTPException(status_code=400, detail=f"Unknown service: {req.service}")
    inv = incident_engine.create_investigation(
        incident_description=req.incident_description,
        service=req.service,
        scenario_id=req.scenario_id,
        depth=req.depth,
    )
    return inv.model_dump()


@router.get("/investigations/{investigation_id}")
def get_investigation(investigation_id: str):
    inv = incident_engine.get_investigation(investigation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return inv.model_dump()


@router.post("/investigations/{investigation_id}/run")
async def run_investigation(investigation_id: str, background_tasks: BackgroundTasks):
    inv = incident_engine.get_investigation(investigation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    if inv.status not in (InvestigationStatus.PENDING, InvestigationStatus.FAILED):
        return {"message": f"Investigation already in state: {inv.status.value}", "investigation_id": investigation_id}
    background_tasks.add_task(incident_engine.run_investigation, investigation_id)
    return {"message": "Investigation started", "investigation_id": investigation_id}


@router.get("/investigations/{investigation_id}/evidence")
def get_evidence(investigation_id: str, evidence_type: Optional[str] = None, severity: Optional[str] = None):
    inv = incident_engine.get_investigation(investigation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    evidence = inv.evidence
    if evidence_type:
        evidence = [e for e in evidence if e.evidence_type == evidence_type]
    if severity:
        evidence = [e for e in evidence if e.severity == severity]
    return [e.model_dump() for e in evidence]


@router.get("/investigations/{investigation_id}/hypotheses")
def get_hypotheses(investigation_id: str):
    inv = incident_engine.get_investigation(investigation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return [h.model_dump() for h in inv.hypotheses]


# ── Remediation ────────────────────────────────────────────────────────────────

@router.post("/investigations/{investigation_id}/remediation/propose")
async def propose_remediation(investigation_id: str):
    inv = incident_engine.get_investigation(investigation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    if not inv.hypotheses:
        raise HTTPException(status_code=400, detail="No hypotheses available — complete investigation first")
    if inv.remediation:
        return inv.remediation.model_dump()
    from app.tools.remediation import propose_remediation as _propose
    try:
        rem = _propose(inv.scenario_id, inv.hypotheses[0].id)
        from app.models.investigation import RemediationStatus
        rem.status = RemediationStatus.AWAITING_APPROVAL
        inv.remediation = rem
        return rem.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/investigations/{investigation_id}/remediation/approve")
async def approve_remediation(investigation_id: str, req: ApproveRemediationRequest):
    inv = incident_engine.get_investigation(investigation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    if not inv.remediation:
        raise HTTPException(status_code=400, detail="No remediation proposed")

    from app.models.investigation import RemediationStatus
    if inv.remediation.status not in (RemediationStatus.PROPOSED, RemediationStatus.AWAITING_APPROVAL):
        raise HTTPException(status_code=400, detail=f"Remediation already in state: {inv.remediation.status.value}")

    updated = await incident_engine.approve_remediation(investigation_id, req.approved)
    return updated.model_dump()


# ── Verification ───────────────────────────────────────────────────────────────

@router.post("/investigations/{investigation_id}/verify")
async def verify_recovery(investigation_id: str):
    inv = incident_engine.get_investigation(investigation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    from app.tools.remediation import verify_recovery as _verify
    result = _verify(investigation_id, inv.scenario_id)
    inv.verification_result = result
    return result.model_dump()


# ── Reports ────────────────────────────────────────────────────────────────────

@router.get("/investigations/{investigation_id}/report")
def get_report(investigation_id: str):
    inv = incident_engine.get_investigation(investigation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    if not inv.report:
        if inv.status == InvestigationStatus.COMPLETED and inv.verification_result:
            from app.services.report_generator import generate_postmortem
            inv.report = generate_postmortem(inv)
        else:
            raise HTTPException(status_code=404, detail="Report not yet available — complete investigation and verification first")
    return inv.report.model_dump()


@router.get("/investigations/{investigation_id}/report/download")
def download_report(investigation_id: str, format: str = "json"):
    inv = incident_engine.get_investigation(investigation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    if not inv.report:
        raise HTTPException(status_code=404, detail="Report not available")

    if format == "markdown":
        content = _report_to_markdown(inv.report)
        return Response(content=content, media_type="text/markdown",
                       headers={"Content-Disposition": f"attachment; filename=report_{investigation_id[:8]}.md"})
    else:
        content = json.dumps(inv.report.model_dump(), indent=2, default=str)
        return Response(content=content, media_type="application/json",
                       headers={"Content-Disposition": f"attachment; filename=report_{investigation_id[:8]}.json"})


@router.post("/investigations/{investigation_id}/report/archive")
async def archive_to_s3(investigation_id: str):
    inv = incident_engine.get_investigation(investigation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    if not inv.report:
        raise HTTPException(status_code=404, detail="Report not available")

    uri = archive_report(investigation_id, inv.report.model_dump())
    if uri:
        return {"status": "archived", "s3_uri": uri}
    configured, status = get_s3_status()
    raise HTTPException(status_code=503, detail=f"S3 archival failed: {status}")


# ── Chat ───────────────────────────────────────────────────────────────────────

@router.post("/chat")
async def chat(req: ChatRequest):
    response = await incident_engine.chat_with_investigation(req.investigation_id, req.message)
    return {"response": response, "timestamp": datetime.utcnow().isoformat()}


# ── Settings / Provider ────────────────────────────────────────────────────────

@router.get("/settings/provider")
def get_provider_status():
    # Bedrock check
    bedrock_configured = False
    bedrock_status = "not_configured"
    if settings.ai_provider == "bedrock":
        try:
            provider, name = get_ai_provider()
            if isinstance(provider, BedrockAIProvider):
                bedrock_configured = provider.available
                bedrock_status = "connected" if provider.available else f"error: {provider.error}"
            else:
                bedrock_status = "fallback_to_local"
        except Exception as e:
            bedrock_status = f"error: {str(e)[:60]}"
    else:
        bedrock_status = "not_selected"

    # S3 check
    s3_configured, s3_status = get_s3_status()

    return ProviderStatus(
        provider=settings.ai_provider,
        bedrock_configured=bedrock_configured,
        bedrock_region=settings.aws_region if settings.ai_provider == "bedrock" else None,
        bedrock_model=settings.bedrock_model_id if settings.ai_provider == "bedrock" else None,
        bedrock_status=bedrock_status,
        s3_configured=s3_configured,
        s3_bucket=settings.s3_bucket,
        s3_status=s3_status,
        demo_mode=settings.ai_provider == "local",
        version=settings.version,
    ).model_dump()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _report_to_markdown(report) -> str:
    lines = [
        f"# Incident Postmortem — {report.service}",
        f"",
        f"**Incident ID:** `{report.incident_id}`  ",
        f"**Severity:** {report.severity}  ",
        f"**Service:** {report.service}  ",
        f"**Start:** {report.start_time}  ",
        f"**End:** {report.end_time or 'N/A'}  ",
        f"**Final Status:** {report.final_status}  ",
        f"",
        f"## Impact",
        f"{report.impact_summary}",
        f"",
        f"## Timeline",
    ]
    for evt in report.timeline:
        lines.append(f"- `{evt.timestamp}` **{evt.title}** — {evt.description}")

    lines += [
        f"",
        f"## Root Cause Assessment",
        report.root_cause_assessment,
        f"",
        f"## Contributing Factors",
    ]
    for cf in report.contributing_factors:
        lines.append(f"- {cf}")

    lines += [
        f"",
        f"## Resolution",
        report.resolution,
        f"",
        f"## What Went Well",
    ]
    for w in report.what_went_well:
        lines.append(f"- {w}")

    lines += [
        f"",
        f"## What Could Improve",
    ]
    for w in report.what_could_improve:
        lines.append(f"- {w}")

    lines += [
        f"",
        f"## Follow-Up Actions",
    ]
    for fa in report.follow_up_actions:
        lines.append(f"- [{fa.get('priority', 'medium').upper()}] {fa.get('action', '')} — {fa.get('rationale', '')}")

    lines += [
        f"",
        f"## Unresolved Questions",
    ]
    for uq in report.unresolved_questions:
        lines.append(f"- {uq}")

    lines.append(f"\n---\n*Generated by IncidentLens AI at {report.generated_at}. Environment: SIMULATED.*")
    return "\n".join(lines)
