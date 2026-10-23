"""
Core investigation engine — orchestrates all tools in sequence.
"""
import os
import json
import asyncio
import uuid
import logging
from datetime import datetime
from typing import Dict, Optional
from app.models.investigation import (
    Investigation, InvestigationStatus, ToolExecution, ToolStatus,
    EvidenceItem, RemediationStatus
)
from app.tools.inspect_service_health import inspect_service_health
from app.tools.inspect_logs import inspect_logs
from app.tools.inspect_metrics import inspect_metrics
from app.tools.inspect_deployments import inspect_deployments
from app.tools.correlate_evidence import correlate_evidence
from app.tools.rank_hypotheses import rank_hypotheses
from app.tools.remediation import propose_remediation, execute_simulated_remediation, verify_recovery
from app.services.ai_provider import get_ai_provider
from app.services.report_generator import generate_postmortem
from app.data.scenarios.scenario_data import ALL_SCENARIOS, SERVICES

logger = logging.getLogger(__name__)

# File-backed shared store so FastAPI (React) and Streamlit stay synchronized
_investigations: Dict[str, Investigation] = {}
STORE_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "investigations_store.json")


def _load_store() -> Dict[str, Investigation]:
    if not os.path.exists(STORE_FILE):
        return _investigations
    try:
        with open(STORE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for k, v in data.items():
                if k not in _investigations or _investigations[k].updated_at < v.get("updated_at", ""):
                    _investigations[k] = Investigation(**v)
    except Exception as e:
        logger.warning(f"Could not load investigations store: {e}")
    return _investigations


def _save_store():
    try:
        os.makedirs(os.path.dirname(STORE_FILE), exist_ok=True)
        with open(STORE_FILE, "w", encoding="utf-8") as f:
            json.dump({k: v.model_dump() for k, v in _investigations.items()}, f, indent=2, default=str)
    except Exception as e:
        logger.warning(f"Could not save investigations store: {e}")


def get_all_investigations():
    _load_store()
    return list(_investigations.values())


def get_investigation(investigation_id: str) -> Optional[Investigation]:
    _load_store()
    return _investigations.get(investigation_id)


def create_investigation(incident_description: str, service: str, scenario_id: str, depth: str = "standard") -> Investigation:
    inv = Investigation(
        id=str(uuid.uuid4()),
        incident_description=incident_description,
        service=service,
        scenario_id=scenario_id,
        depth=depth,
        status=InvestigationStatus.PENDING,
    )
    _investigations[inv.id] = inv
    _save_store()
    return inv


async def run_investigation(investigation_id: str) -> Investigation:
    inv = _investigations.get(investigation_id)
    if not inv:
        raise ValueError(f"Investigation {investigation_id} not found")

    if inv.status not in (InvestigationStatus.PENDING, InvestigationStatus.FAILED):
        return inv

    try:
        await _run_pipeline(inv)
    except Exception as e:
        logger.error(f"Investigation {investigation_id} failed: {e}", exc_info=True)
        inv.status = InvestigationStatus.FAILED
        inv.error = str(e)
        inv.updated_at = datetime.utcnow().isoformat()

    return inv


async def _run_pipeline(inv: Investigation):
    """Execute the full 7-step investigation pipeline."""
    scenario = ALL_SCENARIOS.get(inv.scenario_id)
    if not scenario:
        raise ValueError(f"Scenario {inv.scenario_id} not found")

    inv.status = InvestigationStatus.RUNNING
    inv.updated_at = datetime.utcnow().isoformat()

    steps = [
        ("inspect_service_health", "Inspect Service Health", "Checking current service availability, error rate, and latency metrics"),
        ("inspect_logs", "Collect Error Logs", "Retrieving recent error and warning log entries from the service"),
        ("inspect_metrics", "Collect Resource Metrics", "Gathering CPU, memory, connection, and latency metrics"),
        ("inspect_deployments", "Inspect Deployment History", "Reviewing recent deployments and change summaries"),
        ("correlate_evidence", "Correlate Evidence", "Building temporal correlation map and identifying patterns"),
        ("rank_hypotheses", "Rank Hypotheses", "Scoring candidate root causes based on collected evidence"),
        ("ai_analysis", "AI Evidence Analysis", "Running structured AI analysis on the collected evidence"),
    ]

    # Initialize tool history
    inv.tool_history = [
        ToolExecution(tool_name=s[0], display_name=s[1], description=s[2])
        for s in steps
    ]
    inv.status = InvestigationStatus.COLLECTING_EVIDENCE
    inv.updated_at = datetime.utcnow().isoformat()

    health_data = logs_data = metrics_data = deployment_data = correlation = None

    # ── Step 1: Service Health ─────────────────────────────────────────────────
    tool = inv.tool_history[0]
    await _start_tool(inv, tool)
    try:
        health_data = inspect_service_health(inv.service, inv.scenario_id)
        inv.evidence.append(EvidenceItem(
            timestamp=health_data.get("checked_at", datetime.utcnow().isoformat()),
            source="inspect_service_health",
            service=inv.service,
            severity="critical" if health_data.get("error_rate_percent", 0) > 10 else "warning",
            evidence_type="health",
            summary=f"Error rate: {health_data.get('error_rate_percent')}% | P95: {health_data.get('p95_latency_ms')} ms | Availability: {health_data.get('availability_percent')}%",
            detail=health_data.get("observation", ""),
            relevance="supporting",
            raw=health_data,
        ))
        await _complete_tool(inv, tool, f"Error rate {health_data.get('error_rate_percent')}% (baseline {health_data.get('baseline_error_rate_percent')}%)", 1)
    except Exception as e:
        await _fail_tool(inv, tool, str(e))

    inv.progress = 14
    await asyncio.sleep(0.3)

    # ── Step 2: Logs ───────────────────────────────────────────────────────────
    tool = inv.tool_history[1]
    await _start_tool(inv, tool)
    try:
        logs_data = inspect_logs(inv.service, inv.scenario_id)
        for entry in logs_data.get("log_entries", [])[:5]:
            sev = entry.get("level", "INFO").lower()
            if sev == "error":
                sev = "critical"
            elif sev == "warn":
                sev = "warning"
            else:
                sev = "info"
            inv.evidence.append(EvidenceItem(
                timestamp=entry.get("timestamp", datetime.utcnow().isoformat()),
                source="inspect_logs",
                service=inv.service,
                severity=sev,
                evidence_type="log",
                summary=entry.get("message", "")[:120],
                detail=entry.get("message", ""),
                relevance="supporting" if sev in ("critical", "warning") else "neutral",
                raw=entry,
            ))
        await _complete_tool(inv, tool, logs_data.get("observation", "Logs collected"), logs_data.get("total_entries", 0))
    except Exception as e:
        await _fail_tool(inv, tool, str(e))

    inv.progress = 28
    await asyncio.sleep(0.3)

    # ── Step 3: Metrics ────────────────────────────────────────────────────────
    tool = inv.tool_history[2]
    await _start_tool(inv, tool)
    try:
        metrics_data = inspect_metrics(inv.service, inv.scenario_id)
        inv.evidence.append(EvidenceItem(
            timestamp=metrics_data.get("checked_at", datetime.utcnow().isoformat()),
            source="inspect_metrics",
            service=inv.service,
            severity="warning",
            evidence_type="metric",
            summary=f"CPU: {metrics_data['cpu']['current_percent']}% | Memory: {metrics_data['memory']['current_percent']}% | Connections: {metrics_data['connections']['current_utilization_percent']}%",
            detail=metrics_data.get("observation", ""),
            relevance="supporting",
            raw=metrics_data,
        ))
        await _complete_tool(inv, tool, metrics_data.get("observation", "Metrics collected"), 1)
    except Exception as e:
        await _fail_tool(inv, tool, str(e))

    inv.progress = 42
    await asyncio.sleep(0.3)

    # ── Step 4: Deployments ────────────────────────────────────────────────────
    tool = inv.tool_history[3]
    await _start_tool(inv, tool)
    try:
        deployment_data = inspect_deployments(inv.service, inv.scenario_id)
        if deployment_data.get("most_recent_deployment"):
            dep = deployment_data["most_recent_deployment"]
            inv.evidence.append(EvidenceItem(
                timestamp=dep.get("timestamp", datetime.utcnow().isoformat()),
                source="inspect_deployments",
                service=inv.service,
                severity="info",
                evidence_type="deployment",
                summary=f"Deployment {dep.get('version')} — risk: {dep.get('risk_level')} — {dep.get('files_changed')} files changed",
                detail=f"{dep.get('version')}: {dep.get('change_summary', '')}",
                relevance="supporting",
                raw=dep,
            ))
        await _complete_tool(inv, tool, deployment_data.get("observation", "Deployments collected"), deployment_data.get("total_deployments", 0))
    except Exception as e:
        await _fail_tool(inv, tool, str(e))

    inv.progress = 57
    await asyncio.sleep(0.3)

    # ── Step 5: Correlate Evidence ─────────────────────────────────────────────
    tool = inv.tool_history[4]
    await _start_tool(inv, tool)
    try:
        correlation = correlate_evidence(
            health_data or {}, logs_data or {}, metrics_data or {}, deployment_data or {}, inv.scenario_id
        )
        inv.evidence.append(EvidenceItem(
            timestamp=datetime.utcnow().isoformat(),
            source="correlate_evidence",
            service=inv.service,
            severity="info",
            evidence_type="correlation",
            summary=f"Correlation strength: {correlation.get('correlation_strength', 'unknown')}",
            detail=correlation.get("temporal_summary", ""),
            relevance="neutral",
            raw=correlation,
        ))
        await _complete_tool(inv, tool, correlation.get("temporal_summary", "Correlation complete"), len(correlation.get("correlated_events", [])))
    except Exception as e:
        await _fail_tool(inv, tool, str(e))

    inv.progress = 71
    await asyncio.sleep(0.3)

    # ── Step 6: Rank Hypotheses ────────────────────────────────────────────────
    inv.status = InvestigationStatus.ANALYZING
    tool = inv.tool_history[5]
    await _start_tool(inv, tool)
    try:
        hypotheses = rank_hypotheses(correlation or {}, inv.scenario_id)
        inv.hypotheses = hypotheses
        await _complete_tool(inv, tool, f"{len(hypotheses)} hypotheses ranked", len(hypotheses))
    except Exception as e:
        await _fail_tool(inv, tool, str(e))

    inv.progress = 85
    await asyncio.sleep(0.3)

    # ── Step 7: AI Analysis ────────────────────────────────────────────────────
    tool = inv.tool_history[6]
    await _start_tool(inv, tool)
    try:
        evidence_for_ai = {
            "health": health_data,
            "log_summary": {k: v for k, v in (logs_data or {}).items() if k != "log_entries"},
            "top_logs": (logs_data or {}).get("log_entries", [])[:3],
            "metrics_observation": (metrics_data or {}).get("observation"),
            "deployment_observation": (deployment_data or {}).get("observation"),
            "correlation": {k: v for k, v in (correlation or {}).items() if k != "correlated_events"},
        }
        provider, provider_name = get_ai_provider()
        ai_result = provider.analyze_evidence(evidence_for_ai, inv.scenario_id)
        inv.ai_provider_used = provider_name
        inv.evidence.append(EvidenceItem(
            timestamp=datetime.utcnow().isoformat(),
            source="ai_analysis",
            service=inv.service,
            severity="info",
            evidence_type="interpretation",
            summary=ai_result.get("summary", "AI analysis complete")[:200],
            detail=ai_result.get("summary", "") + "\n\nUncertainty: " + ai_result.get("uncertainty", ""),
            relevance="neutral",
            raw=ai_result,
        ))
        await _complete_tool(inv, tool, f"Analysis complete via {provider_name}", 1)
    except Exception as e:
        await _fail_tool(inv, tool, str(e))
        inv.ai_provider_used = "local_simulation"

    inv.progress = 92

    # ── Propose remediation ────────────────────────────────────────────────────
    try:
        if inv.hypotheses:
            top_hypothesis = inv.hypotheses[0]
            remediation = propose_remediation(inv.scenario_id, top_hypothesis.id)
            remediation.status = RemediationStatus.AWAITING_APPROVAL
            inv.remediation = remediation
    except Exception as e:
        logger.warning(f"Remediation proposal failed: {e}")

    inv.status = InvestigationStatus.AWAITING_APPROVAL if inv.remediation else InvestigationStatus.COMPLETED
    inv.progress = 100
    inv.updated_at = datetime.utcnow().isoformat()
    _save_store()


async def approve_remediation(investigation_id: str, approved: bool) -> Investigation:
    inv = _investigations.get(investigation_id)
    if not inv:
        raise ValueError(f"Investigation {investigation_id} not found")
    if not inv.remediation:
        raise ValueError("No remediation proposed for this investigation")

    if not approved:
        inv.remediation.status = RemediationStatus.REJECTED
        inv.status = InvestigationStatus.COMPLETED
        inv.updated_at = datetime.utcnow().isoformat()
        _save_store()
        return inv

    # Execute simulation
    inv.remediation.status = RemediationStatus.EXECUTING
    inv.status = InvestigationStatus.REMEDIATING
    inv.updated_at = datetime.utcnow().isoformat()

    try:
        result = execute_simulated_remediation(inv.id, inv.remediation.action_id, inv.scenario_id)
        inv.remediation_result = result
        inv.remediation.status = RemediationStatus.COMPLETED
        inv.remediation.executed_at = result.timestamp
        inv.remediation.approved_at = datetime.utcnow().isoformat()
    except Exception as e:
        inv.remediation.status = RemediationStatus.FAILED
        inv.error = str(e)
        inv.status = InvestigationStatus.FAILED
        _save_store()
        return inv

    # Verify recovery
    inv.status = InvestigationStatus.VERIFYING
    try:
        ver_result = verify_recovery(inv.id, inv.scenario_id)
        inv.verification_result = ver_result
    except Exception as e:
        logger.error(f"Verification failed: {e}")

    # Generate report
    try:
        report = generate_postmortem(inv)
        inv.report = report
    except Exception as e:
        logger.warning(f"Report generation failed: {e}")

    inv.status = InvestigationStatus.COMPLETED
    inv.completed_at = datetime.utcnow().isoformat()
    inv.updated_at = datetime.utcnow().isoformat()
    _save_store()
    return inv


async def chat_with_investigation(investigation_id: str, message: str) -> str:
    inv = _investigations.get(investigation_id)
    if not inv:
        return "Investigation not found. Please start or select an active investigation."

    provider, _ = get_ai_provider()

    context = {
        "scenario_id": inv.scenario_id,
        "service": inv.service,
        "status": inv.status.value,
        "hypotheses": [h.model_dump() for h in inv.hypotheses],
        "evidence": [e.model_dump() for e in inv.evidence],
        "remediation": inv.remediation.model_dump() if inv.remediation else None,
        "verification_result": inv.verification_result.model_dump() if inv.verification_result else None,
    }

    response = provider.chat_response(message, context)
    inv.chat_messages.append({"role": "user", "content": message, "timestamp": datetime.utcnow().isoformat()})
    inv.chat_messages.append({"role": "assistant", "content": response, "timestamp": datetime.utcnow().isoformat()})
    _save_store()
    return response


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _start_tool(inv: Investigation, tool: ToolExecution):
    tool.status = ToolStatus.RUNNING
    tool.started_at = datetime.utcnow().isoformat()
    inv.updated_at = datetime.utcnow().isoformat()
    await asyncio.sleep(0.1)


async def _complete_tool(inv: Investigation, tool: ToolExecution, summary: str, evidence_count: int):
    tool.status = ToolStatus.COMPLETED
    tool.completed_at = datetime.utcnow().isoformat()
    tool.result_summary = summary
    tool.evidence_count = evidence_count
    inv.updated_at = datetime.utcnow().isoformat()


async def _fail_tool(inv: Investigation, tool: ToolExecution, error: str):
    tool.status = ToolStatus.FAILED
    tool.completed_at = datetime.utcnow().isoformat()
    tool.error = error
    inv.updated_at = datetime.utcnow().isoformat()
    logger.error(f"Tool {tool.tool_name} failed: {error}")
