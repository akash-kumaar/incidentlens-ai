"""
Report generator: builds a PostmortemReport from investigation state.
"""
from datetime import datetime
from typing import List
from app.models.investigation import Investigation, PostmortemReport, TimelineEvent
from app.data.scenarios.scenario_data import ALL_SCENARIOS, SERVICES


def generate_postmortem(inv: Investigation) -> PostmortemReport:
    scenario = ALL_SCENARIOS.get(inv.scenario_id, {})
    service = SERVICES.get(inv.service, {"name": inv.service})
    top_hyp = inv.hypotheses[0] if inv.hypotheses else None
    ver = inv.verification_result

    # Build timeline from scenario events + investigation actions
    timeline_events = []
    for evt in scenario.get("timeline_events", []):
        timeline_events.append(TimelineEvent(
            timestamp=evt["timestamp"],
            type=evt["type"],
            title=evt["title"],
            description=evt["description"],
            severity=evt.get("severity", "info"),
        ))

    if inv.remediation and inv.remediation.executed_at:
        timeline_events.append(TimelineEvent(
            timestamp=inv.remediation.executed_at,
            type="remediation",
            title=f"Remediation executed: {inv.remediation.title}",
            description=inv.remediation.description,
            severity="info",
        ))

    if ver and inv.completed_at:
        timeline_events.append(TimelineEvent(
            timestamp=inv.completed_at,
            type="verification",
            title=f"Recovery verification: {'passed' if ver.passed else 'failed'}",
            description=f"Final status: {ver.final_status}",
            severity="info" if ver.passed else "warning",
        ))

    timeline_events.sort(key=lambda e: e.timestamp)

    # Root cause assessment
    if top_hyp:
        rca = (
            f"{top_hyp.title} ({top_hyp.confidence.value.replace('_', ' ').title()}). "
            f"{top_hyp.confidence_explanation}"
        )
        contributing = top_hyp.supporting_evidence[:3]
        follow_ups = [
            {"action": top_hyp.recommended_verification, "priority": "high", "rationale": "Required to confirm root cause"},
            {"action": top_hyp.recommended_action, "priority": "high", "rationale": "Primary resolution step"},
        ]
        if top_hyp.missing_evidence:
            follow_ups.append({
                "action": f"Collect missing evidence: {top_hyp.missing_evidence[0]}",
                "priority": "medium",
                "rationale": "Reduces uncertainty in root cause assessment",
            })
    else:
        rca = "Root cause could not be determined — insufficient evidence collected."
        contributing = []
        follow_ups = []

    # Resolution description
    if inv.remediation_result and ver:
        if ver.passed:
            resolution = (
                f"Simulated remediation executed: {inv.remediation.title if inv.remediation else 'unknown'}. "
                f"All {len(ver.checks)} verification checks passed. "
                f"Service recovered to baseline metrics. Final status: {ver.final_status}."
            )
        else:
            resolution = (
                f"Remediation executed but some verification checks did not pass. "
                f"Remaining issues: {'; '.join(ver.remaining_issues)}. "
                f"Further investigation may be required."
            )
    else:
        resolution = "No remediation was executed during this investigation."

    # What went well / could improve
    what_went_well = [
        "Investigation evidence was collected automatically from multiple monitoring sources",
        "Root cause hypothesis generated with explicit supporting and contradictory evidence",
        "Remediation required explicit approval before execution — no automatic changes made",
    ]
    what_could_improve = [
        "Alert detection occurred after the incident was already impacting users — improve proactive monitoring thresholds",
        "Missing observability data identified in investigation — add metrics and structured logging recommended in follow-up actions",
    ]

    return PostmortemReport(
        incident_id=inv.id,
        service=service.get("name", inv.service),
        severity=scenario.get("severity", "unknown"),
        start_time=scenario.get("timeline_events", [{}])[0].get("timestamp", inv.created_at) if scenario.get("timeline_events") else inv.created_at,
        end_time=inv.completed_at,
        impact_summary=scenario.get("description", "No description available."),
        final_status="resolved" if (ver and ver.passed) else ("partial" if ver else "unresolved"),
        timeline=timeline_events,
        root_cause_assessment=rca,
        contributing_factors=contributing,
        resolution=resolution,
        what_went_well=what_went_well,
        what_could_improve=what_could_improve,
        follow_up_actions=follow_ups,
        unresolved_questions=top_hyp.missing_evidence if top_hyp else ["Insufficient evidence collected"],
        generated_at=datetime.utcnow().isoformat(),
    )
