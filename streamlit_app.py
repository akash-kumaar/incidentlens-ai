"""
IncidentLens AI — Streamlit Observability & Incident Investigation Dashboard
Autonomous agentic production incident investigator deployed on Streamlit Community Cloud.
Mirrors the React 19 architecture: Overview, Investigations, Services, Evidence, Reports, and Settings.
"""
import os
import sys
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List

import streamlit as st
import pandas as pd

# ── Ensure backend packages are importable anywhere (local or Streamlit Cloud) ─
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# ── Bridge Streamlit Cloud secrets to environment variables if provided ───────
try:
    if hasattr(st, "secrets"):
        for sec_key in ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION", "BEDROCK_MODEL_ID", "AI_PROVIDER", "S3_BUCKET"]:
            if sec_key in st.secrets and sec_key not in os.environ:
                os.environ[sec_key] = str(st.secrets[sec_key])
except Exception:
    pass

from app.models.investigation import (
    Investigation, InvestigationStatus, ConfidenceCategory,
    Severity, RemediationStatus, ToolStatus
)
from app.services import incident_engine
from app.data.scenarios.scenario_data import ALL_SCENARIOS, SERVICES
from app.services.ai_provider import get_ai_provider, BedrockAIProvider
from app.services.s3_archive import get_s3_status
from app.config import settings

# ── Page Configuration ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="IncidentLens AI | Autonomous Incident Investigator",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom SRE / Observability CSS Theme matching React UI ─────────────────────
st.markdown("""
<style>
    /* Metric Cards */
    div[data-testid="stMetric"] {
        background-color: #131b2e;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 14px 18px;
    }
    div[data-testid="stMetricValue"] {
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        font-size: 1.5rem;
        font-weight: 600;
    }
    div[data-testid="stMetricLabel"] {
        color: #94a3b8;
        font-size: 0.85rem;
    }
    
    /* Badges */
    .badge-critical {
        background-color: rgba(239, 68, 68, 0.15);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.35);
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        display: inline-block;
    }
    .badge-warning {
        background-color: rgba(245, 158, 11, 0.15);
        color: #fbbf24;
        border: 1px solid rgba(245, 158, 11, 0.35);
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        display: inline-block;
    }
    .badge-info {
        background-color: rgba(59, 130, 246, 0.15);
        color: #60a5fa;
        border: 1px solid rgba(59, 130, 246, 0.35);
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        display: inline-block;
    }
    .badge-success {
        background-color: rgba(16, 185, 129, 0.15);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.35);
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        display: inline-block;
    }

    /* Cards */
    .incident-card {
        background-color: #131b2e;
        border: 1px solid #1e293b;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 14px;
    }
    .guardrail-box {
        background-color: rgba(245, 158, 11, 0.08);
        border: 1px solid rgba(245, 158, 11, 0.4);
        border-radius: 8px;
        padding: 18px 20px;
        margin: 14px 0;
    }
    .timeline-item {
        border-left: 2px solid #3b82f6;
        padding-left: 14px;
        margin-bottom: 16px;
    }
    .mode-callout {
        padding: 10px 14px;
        border-radius: 6px;
        margin-bottom: 14px;
        font-size: 0.88rem;
    }
</style>
""", unsafe_allow_html=True)


# ── Session State Initialization ───────────────────────────────────────────────
if "current_inv_id" not in st.session_state:
    st.session_state.current_inv_id = None
if "nav_page" not in st.session_state:
    st.session_state.nav_page = "Overview"


# ── Helper Functions ───────────────────────────────────────────────────────────
def run_coroutine(coro):
    """Executes an async coroutine synchronously inside Streamlit."""
    return asyncio.run(coro)


def get_confidence_badge_html(category: ConfidenceCategory) -> str:
    mapping = {
        ConfidenceCategory.STRONGLY_SUPPORTED: ("badge-critical", "Strongly Supported"),
        ConfidenceCategory.PLAUSIBLE: ("badge-warning", "Plausible"),
        ConfidenceCategory.WEAKLY_SUPPORTED: ("badge-info", "Weakly Supported"),
        ConfidenceCategory.INSUFFICIENT_EVIDENCE: ("badge-info", "Insufficient Evidence"),
    }
    css_class, label = mapping.get(category, ("badge-info", str(category)))
    return f'<span class="{css_class}">{label}</span>'


def format_report_to_markdown(report) -> str:
    """Formats a PostmortemReport object into Markdown format."""
    lines = [
        f"# Incident Postmortem — {report.service}",
        "",
        f"**Incident ID:** `{report.incident_id}`  ",
        f"**Severity:** {report.severity}  ",
        f"**Service:** {report.service}  ",
        f"**Start:** {report.start_time}  ",
        f"**End:** {report.end_time or 'N/A'}  ",
        f"**Final Status:** {report.final_status}  ",
        "",
        "## Impact Summary",
        report.impact_summary,
        "",
        "## Incident Timeline",
    ]
    for evt in report.timeline:
        lines.append(f"- `{evt.timestamp}` **{evt.title}** — {evt.description}")

    lines += [
        "",
        "## Root Cause Assessment",
        report.root_cause_assessment,
        "",
        "## Contributing Factors",
    ]
    for cf in report.contributing_factors:
        lines.append(f"- {cf}")

    lines += [
        "",
        "## Resolution & Recovery",
        report.resolution,
        "",
        "## What Went Well",
    ]
    for w in report.what_went_well:
        lines.append(f"- {w}")

    lines += [
        "",
        "## What Could Improve",
    ]
    for w in report.what_could_improve:
        lines.append(f"- {w}")

    lines += [
        "",
        "## Follow-Up Preventive Actions",
    ]
    for fa in report.follow_up_actions:
        lines.append(f"- **[{fa.get('priority', 'medium').upper()}]** {fa.get('action', '')} — *{fa.get('rationale', '')}*")

    lines += [
        "",
        "## Unresolved Questions",
    ]
    for uq in report.unresolved_questions:
        lines.append(f"- {uq}")

    lines.append(f"\n---\n*Generated by IncidentLens AI at {report.generated_at}. Environment: SIMULATED.*")
    return "\n".join(lines)


# ── Navigation & Sidebar ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚡ **IncidentLens**")
    st.caption("AI Production Incident Investigator · v1.0.0")

    # Main Navigation matching React sidebar
    pages = ["Overview", "Investigations", "Services", "Evidence", "Reports", "Settings"]
    current_index = pages.index(st.session_state.nav_page) if st.session_state.nav_page in pages else 0
    selected_page = st.radio(
        "Navigation",
        options=pages,
        index=current_index,
        label_visibility="collapsed"
    )
    if selected_page != st.session_state.nav_page:
        st.session_state.nav_page = selected_page
        st.rerun()

    st.markdown("---")
    st.markdown("#### ⚙️ System Status")

    provider_name = settings.ai_provider
    if provider_name == "bedrock":
        try:
            prov, _ = get_ai_provider()
            if isinstance(prov, BedrockAIProvider) and prov.available:
                st.markdown('<span class="badge-success">● Amazon Bedrock (Claude)</span>', unsafe_allow_html=True)
            else:
                st.markdown('<span class="badge-warning">● Local Fallback (Simulation)</span>', unsafe_allow_html=True)
        except Exception:
            st.markdown('<span class="badge-warning">● Local Simulator</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="badge-info">● Deterministic Scenario Engine</span>', unsafe_allow_html=True)

    s3_ok, _ = get_s3_status()
    if s3_ok:
        st.markdown(f'<span class="badge-success">● S3: {settings.s3_bucket}</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="badge-info">○ S3: Local Export Only</span>', unsafe_allow_html=True)

    st.markdown('<span class="badge-success">🛡️ Human-in-the-Loop Active</span>', unsafe_allow_html=True)

    st.markdown("---")
    st.caption("Shared storage active with FastAPI & React.")


# ── Load Live Investigations ───────────────────────────────────────────────────
all_invs = incident_engine.get_all_investigations()


# ==============================================================================
# VIEW 1: OVERVIEW PAGE (Matches React / overview)
# ==============================================================================
if st.session_state.nav_page == "Overview":
    now_hour = datetime.now().hour
    greeting = "Good morning" if now_hour < 12 else ("Good afternoon" if now_hour < 18 else "Good evening")

    c_title, c_btn = st.columns([8, 2])
    with c_title:
        st.markdown(f"## {greeting}. Let's investigate.")
        st.caption("IncidentLens AI — evidence-driven incident investigation workspace.")
    with c_btn:
        if st.button("➕ Start Investigation", type="primary", use_container_width=True):
            st.session_state.nav_page = "Investigations"
            st.rerun()

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # 4 Top KPIs matching React OverviewPage
    k1, k2, k3, k4 = st.columns(4)
    active_count = len([i for i in all_invs if i.status not in (InvestigationStatus.COMPLETED, InvestigationStatus.FAILED)])
    completed_count = len([i for i in all_invs if i.status == InvestigationStatus.COMPLETED])
    critical_findings = len([i for i in all_invs if any(h.confidence == ConfidenceCategory.STRONGLY_SUPPORTED for h in i.hypotheses)])
    services_affected = len(set(i.service for i in all_invs))

    with k1:
        st.metric("Active Incidents", active_count)
    with k2:
        st.metric("Resolved Incidents", completed_count)
    with k3:
        st.metric("Critical Findings", critical_findings)
    with k4:
        st.metric("Monitored Services", len(SERVICES))

    st.markdown("---")

    # Pre-configured Incident Scenarios Cards
    st.markdown("### ⚡ Pre-Configured Incident Scenarios")
    st.caption("Launch realistic, zero-dependency production incident investigations with 1 click:")

    sc1, sc2, sc3 = st.columns(3)
    
    # Scenario A
    with sc1:
        s_a = ALL_SCENARIOS["scenario-deployment-regression"]
        st.markdown(f"""
        <div class="incident-card">
            <span class="badge-critical">Critical</span> &nbsp; <code>{s_a['service']}</code>
            <h4 style="margin: 8px 0 4px 0;">{s_a['name']}</h4>
            <p style="font-size: 0.85rem; color: #94a3b8; min-height: 48px;">
                {s_a['description']}
            </p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🚀 Investigate API Regression", key="btn_sc_a", use_container_width=True):
            new_inv = incident_engine.create_investigation(
                incident_description=s_a["description"],
                service=s_a["service"],
                scenario_id="scenario-deployment-regression"
            )
            with st.spinner("Analyzing telemetry, logs, and deployment diffs..."):
                run_coroutine(incident_engine.run_investigation(new_inv.id))
            st.session_state.current_inv_id = new_inv.id
            st.session_state.nav_page = "Investigations"
            st.rerun()

    # Scenario B
    with sc2:
        s_b = ALL_SCENARIOS["scenario-db-connection-exhaustion"]
        st.markdown(f"""
        <div class="incident-card">
            <span class="badge-critical">Critical</span> &nbsp; <code>{s_b['service']}</code>
            <h4 style="margin: 8px 0 4px 0;">{s_b['name']}</h4>
            <p style="font-size: 0.85rem; color: #94a3b8; min-height: 48px;">
                {s_b['description']}
            </p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🚀 Investigate DB Saturation", key="btn_sc_b", use_container_width=True):
            new_inv = incident_engine.create_investigation(
                incident_description=s_b["description"],
                service=s_b["service"],
                scenario_id="scenario-db-connection-exhaustion"
            )
            with st.spinner("Analyzing database connection pools and slow queries..."):
                run_coroutine(incident_engine.run_investigation(new_inv.id))
            st.session_state.current_inv_id = new_inv.id
            st.session_state.nav_page = "Investigations"
            st.rerun()

    # Scenario C
    with sc3:
        s_c = ALL_SCENARIOS["scenario-memory-pressure"]
        st.markdown(f"""
        <div class="incident-card">
            <span class="badge-warning">High</span> &nbsp; <code>{s_c['service']}</code>
            <h4 style="margin: 8px 0 4px 0;">{s_c['name']}</h4>
            <p style="font-size: 0.85rem; color: #94a3b8; min-height: 48px;">
                {s_c['description']}
            </p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🚀 Investigate Memory Pressure", key="btn_sc_c", use_container_width=True):
            new_inv = incident_engine.create_investigation(
                incident_description=s_c["description"],
                service=s_c["service"],
                scenario_id="scenario-memory-pressure"
            )
            with st.spinner("Analyzing memory heaps and GC pause timings..."):
                run_coroutine(incident_engine.run_investigation(new_inv.id))
            st.session_state.current_inv_id = new_inv.id
            st.session_state.nav_page = "Investigations"
            st.rerun()

    st.markdown("---")

    # Recent Investigations Table
    st.markdown("### 📋 Recent Investigations")
    if not all_invs:
        st.info("No investigations executed yet. Click one of the scenarios above to launch your first investigation!")
    else:
        recent_rows = []
        for i in reversed(all_invs[:6]):
            top_hyp = i.hypotheses[0].title if i.hypotheses else "Analyzing..."
            recent_rows.append({
                "Target Service": i.service,
                "Status": i.status.value.replace("_", " ").title(),
                "Leading Hypothesis": top_hyp,
                "Evidence Items": len(i.evidence),
                "Created At": i.created_at[:19],
                "ID": i.id,
            })
        st.dataframe(pd.DataFrame(recent_rows).drop(columns=["ID"]), use_container_width=True, hide_index=True)


# ==============================================================================
# VIEW 2: INVESTIGATIONS PAGE (Detailed workspace)
# ==============================================================================
elif st.session_state.nav_page == "Investigations":
    inv: Optional[Investigation] = None
    if st.session_state.current_inv_id:
        inv = incident_engine.get_investigation(st.session_state.current_inv_id)

    # Top selector bar
    top_c1, top_c2 = st.columns([7, 3])
    with top_c1:
        if all_invs:
            inv_map = {
                f"{i.service} ({i.status.value}) — {i.created_at[11:19]}": i.id
                for i in reversed(all_invs)
            }
            default_idx = (
                list(inv_map.values()).index(st.session_state.current_inv_id)
                if st.session_state.current_inv_id in inv_map.values() else 0
            )
            chosen_inv_label = st.selectbox(
                "Select Investigation Workspace",
                options=list(inv_map.keys()),
                index=default_idx
            )
            st.session_state.current_inv_id = inv_map[chosen_inv_label]
            inv = incident_engine.get_investigation(st.session_state.current_inv_id)
    with top_c2:
        with st.popover("➕ New Investigation"):
            scenario_opts = {s["name"]: s["id"] for s in ALL_SCENARIOS.values()}
            chosen_sc_name = st.selectbox("Scenario", options=list(scenario_opts.keys()))
            chosen_sc_id = scenario_opts[chosen_sc_name]
            meta = ALL_SCENARIOS[chosen_sc_id]
            desc_override = st.text_area("Incident Notes", value=meta["description"], height=60)
            if st.button("Launch", type="primary", use_container_width=True):
                new_inv = incident_engine.create_investigation(
                    incident_description=desc_override,
                    service=meta["service"],
                    scenario_id=chosen_sc_id
                )
                with st.spinner("Analyzing..."):
                    run_coroutine(incident_engine.run_investigation(new_inv.id))
                st.session_state.current_inv_id = new_inv.id
                st.rerun()

    if not inv:
        st.info("No investigation selected. Launch one above or return to the Overview tab.")
        st.stop()

    # Investigation Title
    st.markdown(f"## 🔍 Investigation: `{inv.service}`")
    
    # Clear engine mode callout (Requirement 7)
    if inv.ai_provider_used == "bedrock":
        st.markdown("""
        <div class="mode-callout" style="background-color: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3);">
            <strong>🤖 AI Provider: Amazon Bedrock (Claude 3.5 Sonnet)</strong> — Generative AI correlation across telemetry & traces.
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="mode-callout" style="background-color: rgba(59, 130, 246, 0.1); border: 1px solid rgba(59, 130, 246, 0.3);">
            <strong>⚙️ Diagnostic Engine: Deterministic Scenario-Based Analysis</strong> — High-fidelity offline heuristic analysis (No External Credentials Required).
        </div>
        """, unsafe_allow_html=True)

    st.caption(f"Investigation ID: `{inv.id}` | Created: `{inv.created_at[:19]}`")

    # Status and Top KPI Row
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Status", inv.status.value.replace("_", " ").title())
    with m2:
        top_h = inv.hypotheses[0].title if inv.hypotheses else "Analyzing..."
        st.metric("Leading Hypothesis", top_h[:24] + "...")
    with m3:
        top_c = inv.hypotheses[0].confidence.value.replace("_", " ").title() if inv.hypotheses else "Pending"
        st.metric("Confidence", top_c)
    with m4:
        st.metric("Correlated Evidence", len(inv.evidence))

    st.markdown("---")

    # Pipeline Stepper
    st.markdown("### 🛠️ Diagnostic Agent Pipeline")
    cols = st.columns(len(inv.tool_history)) if inv.tool_history else [st.container()]
    for idx, tool in enumerate(inv.tool_history):
        with cols[idx]:
            if tool.status == ToolStatus.COMPLETED:
                st.markdown(f"**✅ {tool.display_name}**")
                st.caption(f"{tool.result_summary or 'Completed'} ({tool.evidence_count} items)")
            elif tool.status == ToolStatus.FAILED:
                st.markdown(f"**❌ {tool.display_name}**")
                st.caption(f"Failed: {tool.error}")
            else:
                st.markdown(f"**⏳ {tool.display_name}**")
                st.caption("Pending")

    st.markdown("---")

    # Content Tabs
    tab_hyp, tab_rem, tab_ev, tab_rep, tab_chat = st.tabs([
        "🎯 Ranked Hypotheses",
        "🛡️ Remediation & Guardrails",
        "📊 Evidence Explorer",
        "📝 Postmortem Report",
        "💬 SRE Assistant Q&A"
    ])

    with tab_hyp:
        st.markdown("### 🏆 Root Cause Hypotheses (Ranked by Evidence)")
        for hyp in inv.hypotheses:
            badge_html = get_confidence_badge_html(hyp.confidence)
            st.markdown(f"""
            <div class="incident-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h4 style="margin: 0;">Rank #{hyp.rank}: {hyp.title}</h4>
                    {badge_html}
                </div>
                <p style="color: #cbd5e1; margin-top: 8px; font-size: 0.95rem;">
                    {hyp.confidence_explanation}
                </p>
            </div>
            """, unsafe_allow_html=True)

            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**🟢 Supporting Evidence:**")
                for sup in hyp.supporting_evidence:
                    st.markdown(f"- {sup}")
            with col_b:
                st.markdown("**🔴 Contradictory Evidence:**")
                if hyp.contradictory_evidence:
                    for con in hyp.contradictory_evidence:
                        st.markdown(f"- {con}")
                else:
                    st.caption("No contradictory evidence identified.")

            st.markdown(f"**Recommended Action:** `{hyp.recommended_action}`")
            st.markdown(f"**Verification Step:** `{hyp.recommended_verification}`")
            st.divider()

    with tab_rem:
        st.markdown("### 🛡️ Human-in-the-Loop Remediation Guardrails")
        if not inv.remediation:
            st.info("No remediation action currently proposed.")
        else:
            rem = inv.remediation
            st.markdown(f"""
            <div class="guardrail-box">
                <h4 style="color: #fbbf24; margin: 0 0 8px 0;">⚠️ Action Awaiting Authorization: {rem.title}</h4>
                <p style="font-size: 0.95rem; color: #f1f5f9;"><strong>Rationale:</strong> {rem.reason}</p>
                <p style="font-size: 0.95rem; color: #f1f5f9;"><strong>Expected Outcome:</strong> {rem.expected_outcome}</p>
                <p style="font-size: 0.95rem; color: #94a3b8;"><strong>Environment Change:</strong> {rem.what_will_change}</p>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("**Identified Operational Risks:**")
            for risk in rem.risks:
                st.markdown(f"- ⚠️ {risk}")

            if rem.status == RemediationStatus.AWAITING_APPROVAL:
                ca, cb, _ = st.columns([2, 2, 4])
                with ca:
                    if st.button("✅ Authorize & Execute", type="primary", use_container_width=True):
                        with st.spinner("Executing remediation and running health verification..."):
                            run_coroutine(incident_engine.approve_remediation(inv.id, True))
                        st.success("Remediation executed and recovery verified!")
                        st.rerun()
                with cb:
                    if st.button("❌ Reject Proposed Action", use_container_width=True):
                        run_coroutine(incident_engine.approve_remediation(inv.id, False))
                        st.warning("Action rejected by engineer.")
                        st.rerun()
            elif rem.status == RemediationStatus.COMPLETED:
                st.success(f"Remediation executed at `{rem.executed_at[:19]}`. Recovery verified.")
                if inv.verification_result:
                    ver = inv.verification_result
                    v_df = pd.DataFrame([
                        {"Metric": k, "Before Remediation": str(v), "After Recovery": str(ver.after_metrics.get(k, "N/A"))}
                        for k, v in ver.before_metrics.items()
                    ])
                    st.dataframe(v_df, use_container_width=True, hide_index=True)
                    st.markdown(f"**Verification Checks:** `{'ALL PASSED' if ver.passed else 'FAILED'}` | **State:** `{ver.final_status}`")

    with tab_ev:
        st.markdown("### 📊 Correlated Diagnostic Evidence")
        sc_m = ALL_SCENARIOS.get(inv.scenario_id, {})
        if "metrics" in sc_m:
            with st.expander("📈 Baseline vs Incident Telemetry", expanded=True):
                p_pre = sc_m["metrics"].get("pre_incident", {})
                p_post = sc_m["metrics"].get("post_incident", {})
                m_rows = []
                for k in p_pre.keys():
                    m_rows.append({
                        "Metric": k.replace("_", " ").title(),
                        "Pre-Incident Baseline": p_pre.get(k),
                        "During Incident": p_post.get(k),
                    })
                st.dataframe(pd.DataFrame(m_rows), use_container_width=True, hide_index=True)

        ev_src = ["All"] + list(set(e.evidence_type for e in inv.evidence))
        chosen_src = st.selectbox("Filter Source", options=ev_src)
        for e in [x for x in inv.evidence if chosen_src == "All" or x.evidence_type == chosen_src]:
            badge = "badge-critical" if e.severity in ("critical", "high") else ("badge-warning" if e.severity == "warning" else "badge-info")
            with st.expander(f"[{e.evidence_type.upper()}] {e.summary[:100]}..."):
                st.markdown(f"<span class='{badge}'>{e.severity.upper()}</span> &nbsp; Tool: <code>{e.source}</code>", unsafe_allow_html=True)
                st.markdown(f"**Finding:** {e.detail}")
                if e.raw:
                    st.json(e.raw)

    with tab_rep:
        st.markdown("### 📝 Incident Postmortem & Retrospective")
        if not inv.report:
            st.info("Postmortem report will be assembled automatically once remediation is approved and verified.")
        else:
            rep = inv.report
            st.markdown(f"#### Executive Summary — `{rep.service}` Outage")
            st.markdown(f"**Impact:** {rep.impact_summary}")
            st.markdown(f"**Root Cause:** {rep.root_cause_assessment}")

            st.markdown("---")
            st.markdown("#### Chronological Incident Timeline")
            for evt in rep.timeline:
                st.markdown(f"""
                <div class="timeline-item">
                    <span style="color: #60a5fa; font-family: monospace; font-size: 0.85rem;">{evt.timestamp}</span><br>
                    <strong>{evt.title}</strong><br>
                    <span style="color: #94a3b8; font-size: 0.9rem;">{evt.description}</span>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("---")
            c_d1, c_d2, _ = st.columns([2, 2, 4])
            with c_d1:
                st.download_button("📥 Download Markdown", data=format_report_to_markdown(rep), file_name=f"postmortem_{inv.id[:8]}.md", mime="text/markdown", use_container_width=True)
            with c_d2:
                st.download_button("📥 Download JSON", data=json.dumps(rep.model_dump(), indent=2, default=str), file_name=f"postmortem_{inv.id[:8]}.json", mime="application/json", use_container_width=True)

    with tab_chat:
        st.markdown("### 💬 Ask IncidentLens AI")
        st.caption("Interact with the investigation agent regarding root cause reasoning, contradictory evidence, and logs.")
        
        qc1, qc2, qc3, qc4 = st.columns(4)
        quick_msg = None
        with qc1:
            if st.button("Leading root cause?", use_container_width=True):
                quick_msg = "Why did you choose the leading root cause?"
        with qc2:
            if st.button("Contradictory evidence?", use_container_width=True):
                quick_msg = "What contradictory evidence was found?"
        with qc3:
            if st.button("Log findings?", use_container_width=True):
                quick_msg = "What were the key log findings?"
        with qc4:
            if st.button("Remediation rationale?", use_container_width=True):
                quick_msg = "What does the proposed remediation action do?"

        for msg in inv.chat_messages:
            role = msg.get("role", "assistant")
            with st.chat_message(role):
                st.markdown(msg.get("content", ""))

        prompt = st.chat_input("Ask a question about this incident...") or quick_msg
        if prompt:
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.spinner("Analyzing..."):
                reply = run_coroutine(incident_engine.chat_with_investigation(inv.id, prompt))
            with st.chat_message("assistant"):
                st.markdown(reply)
            st.rerun()


# ==============================================================================
# VIEW 3: SERVICES CATALOG PAGE (Matches React /services)
# ==============================================================================
elif st.session_state.nav_page == "Services":
    st.markdown("## 🖥️ Monitored Services")
    st.caption("Current operational health, latency metrics, and baselines across service dependencies.")

    s_rows = []
    for s_id, s_data in SERVICES.items():
        s_rows.append({
            "Service ID": s_id,
            "Service Name": s_data["name"],
            "Description": s_data.get("description", ""),
            "Tier": s_data.get("tier", "tier-1"),
            "Owner Team": s_data.get("owner", "Platform SRE"),
            "Dependencies": ", ".join(s_data.get("dependencies", [])),
        })
    st.dataframe(pd.DataFrame(s_rows), use_container_width=True, hide_index=True)


# ==============================================================================
# VIEW 4: EVIDENCE EXPLORER PAGE (Matches React /evidence)
# ==============================================================================
elif st.session_state.nav_page == "Evidence":
    st.markdown("## 🗄️ Correlated Evidence Explorer")
    st.caption("Browse all collected evidence artifacts across active and historic investigations.")

    all_evidence = []
    for i in all_invs:
        for ev in i.evidence:
            all_evidence.append({
                "Timestamp": ev.timestamp[:19],
                "Service": ev.service,
                "Source Tool": ev.source,
                "Type": ev.evidence_type.upper(),
                "Severity": ev.severity.upper(),
                "Summary": ev.summary,
            })
    if not all_evidence:
        st.info("No evidence collected yet. Start an investigation from the Overview page.")
    else:
        st.dataframe(pd.DataFrame(all_evidence), use_container_width=True, hide_index=True)


# ==============================================================================
# VIEW 5: POSTMORTEM REPORTS PAGE (Matches React /reports)
# ==============================================================================
elif st.session_state.nav_page == "Reports":
    st.markdown("## 📑 Postmortem Retrospective Reports")
    st.caption("Formal incident postmortems generated after recovery verification.")

    completed_reports = [i for i in all_invs if i.report is not None]
    if not completed_reports:
        st.info("No postmortem reports generated yet. Authorize remediation on an investigation to generate its postmortem.")
    else:
        for r_inv in completed_reports:
            r = r_inv.report
            with st.expander(f"Postmortem: {r.service} ({r.severity.upper()}) — {r.start_time[:19]}"):
                st.markdown(f"**Impact:** {r.impact_summary}")
                st.markdown(f"**Root Cause:** {r.root_cause_assessment}")
                st.markdown(f"**Resolution:** {r.resolution}")
                st.download_button("📥 Download Report (Markdown)", data=format_report_to_markdown(r), file_name=f"postmortem_{r.service}.md", key=f"dl_md_{r_inv.id}")


# ==============================================================================
# VIEW 6: SETTINGS PAGE (Matches React /settings)
# ==============================================================================
elif st.session_state.nav_page == "Settings":
    st.markdown("## ⚙️ Settings & Integrations")
    st.caption("Configure optional Amazon Bedrock foundation models and S3 cold storage archives.")

    st.markdown("""
    <div class="incident-card">
        <h4>Environment & AI Provider Mode</h4>
        <p style="font-size: 0.9rem; color: #94a3b8;">
            IncidentLens AI functions out-of-the-box in local demo mode with 3 pre-seeded incidents.
            To hook into your real AWS Bedrock or S3 environment, configure environment variables or Streamlit secrets:
        </p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Amazon Bedrock (Claude)**")
        st.code("""
AI_PROVIDER=bedrock
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
AWS_ACCESS_KEY_ID=<your-access-key-id>
AWS_SECRET_ACCESS_KEY=<your-secret-access-key>
        """, language="bash")
    with c2:
        st.markdown("**AWS S3 Cold Storage Archive**")
        st.code("""
S3_BUCKET=my-incident-reports-bucket
S3_REPORTS_PREFIX=incidentlens/reports/
        """, language="bash")
