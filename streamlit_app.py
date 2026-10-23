"""
IncidentLens AI — Streamlit Observability & Incident Investigation Dashboard
Autonomous agentic production incident investigator deployed on Streamlit Community Cloud.
"""
import os
import sys
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

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
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom SRE / Observability CSS Theme ─────────────────────────────────────────
st.markdown("""
<style>
    /* Metric Cards */
    div[data-testid="stMetric"] {
        background-color: #131b2e;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 12px 16px;
    }
    div[data-testid="stMetricValue"] {
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        font-size: 1.4rem;
    }
    
    /* Badges */
    .badge-critical {
        background-color: rgba(239, 68, 68, 0.15);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.3);
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
        border: 1px solid rgba(245, 158, 11, 0.3);
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
        border: 1px solid rgba(59, 130, 246, 0.3);
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
        border: 1px solid rgba(16, 185, 129, 0.3);
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
        padding: 16px;
        margin-bottom: 12px;
    }
    .guardrail-box {
        background-color: rgba(245, 158, 11, 0.08);
        border: 1px solid rgba(245, 158, 11, 0.35);
        border-radius: 8px;
        padding: 16px;
        margin: 12px 0;
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
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)


# ── Session State Initialization ───────────────────────────────────────────────
if "current_inv_id" not in st.session_state:
    st.session_state.current_inv_id = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


# ── Helper Functions ───────────────────────────────────────────────────────────
def run_coroutine(coro):
    """Executes an async coroutine synchronously inside Streamlit."""
    return asyncio.run(coro)


def get_confidence_badge_html(category: ConfidenceCategory) -> str:
    mapping = {
        ConfidenceCategory.STRONGLY_SUPPORTED: ("badge-critical", "Strongly Supported (High Confidence)"),
        ConfidenceCategory.PLAUSIBLE: ("badge-warning", "Plausible (Medium Confidence)"),
        ConfidenceCategory.WEAKLY_SUPPORTED: ("badge-info", "Weakly Supported (Low Confidence)"),
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


# ── Sidebar: System Status & Scenario Launcher ─────────────────────────────────
with st.sidebar:
    st.markdown("## 🔍 **IncidentLens AI**")
    st.caption("Autonomous Agentic Production Incident Investigator")

    st.markdown("---")
    st.markdown("### ⚙️ System Status")

    # Provider status
    provider_name = settings.ai_provider
    is_bedrock_live = False
    if provider_name == "bedrock":
        try:
            prov, _ = get_ai_provider()
            if isinstance(prov, BedrockAIProvider) and prov.available:
                is_bedrock_live = True
                st.markdown('<span class="badge-success">● Amazon Bedrock (Claude)</span>', unsafe_allow_html=True)
            else:
                st.markdown('<span class="badge-warning">● Local Fallback (No AWS Credentials)</span>', unsafe_allow_html=True)
        except Exception:
            st.markdown('<span class="badge-warning">● Local Fallback (Simulation Mode)</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="badge-info">● Deterministic Scenario Engine (Local)</span>', unsafe_allow_html=True)

    # S3 status
    s3_ok, s3_msg = get_s3_status()
    if s3_ok:
        st.markdown(f'<span class="badge-success">● S3 Archive: {settings.s3_bucket}</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="badge-info">○ S3: Local Export Only</span>', unsafe_allow_html=True)

    st.markdown('<span class="badge-success">🛡️ Guardrail: Human-in-the-Loop Active</span>', unsafe_allow_html=True)

    with st.expander("🔑 Cloud Credentials & Settings"):
        st.caption("IncidentLens AI works 100% offline in local demo mode. Configure these only if using real Amazon Bedrock or S3:")
        new_provider = st.selectbox("AI Engine", options=["local", "bedrock"], index=0 if settings.ai_provider == "local" else 1)
        new_region = st.text_input("AWS Region", value=settings.aws_region)
        new_model = st.text_input("Bedrock Model ID", value=settings.bedrock_model_id)
        new_bucket = st.text_input("S3 Bucket (Optional)", value=settings.s3_bucket or "")
        if st.button("Apply Engine Configuration"):
            settings.ai_provider = new_provider
            settings.aws_region = new_region
            settings.bedrock_model_id = new_model
            settings.s3_bucket = new_bucket if new_bucket.strip() else None
            st.success("Configuration updated!")
            st.rerun()

    st.markdown("---")
    st.markdown("### 🚨 Scenario Selector")

    scenario_options = {
        f"{s['name']} ({s['service']})": s["id"]
        for s in ALL_SCENARIOS.values()
    }
    selected_scenario_name = st.selectbox(
        "Select Incident Scenario",
        options=list(scenario_options.keys()),
        index=0
    )
    scenario_id = scenario_options[selected_scenario_name]
    scenario_meta = ALL_SCENARIOS[scenario_id]

    st.markdown(f"**Target Service:** `{scenario_meta['service']}`")
    st.markdown(f"**Severity:** `{scenario_meta['severity'].upper()}`")
    st.caption(scenario_meta["description"])

    depth = st.select_slider(
        "Diagnostic Depth",
        options=["quick", "standard", "deep"],
        value="standard"
    )

    incident_desc = st.text_area(
        "Incident Description (Optional Override)",
        value=scenario_meta["description"],
        height=75
    )

    if st.button("🚀 Launch AI Investigation", type="primary", use_container_width=True):
        new_inv = incident_engine.create_investigation(
            incident_description=incident_desc,
            service=scenario_meta["service"],
            scenario_id=scenario_id,
            depth=depth
        )
        with st.spinner("Autonomous agent analyzing telemetry, logs, and traces..."):
            run_coroutine(incident_engine.run_investigation(new_inv.id))
        st.session_state.current_inv_id = new_inv.id
        st.success(f"Investigation completed for {scenario_meta['service']}")
        st.rerun()

    st.markdown("---")
    st.markdown("### 📂 Investigation History")
    all_invs = incident_engine.get_all_investigations()
    if all_invs:
        inv_labels = {
            f"{i.service} ({i.status.value}) - {i.created_at[11:19]}": i.id
            for i in reversed(all_invs)
        }
        current_selection = st.selectbox(
            "Switch Investigation",
            options=list(inv_labels.keys()),
            index=0 if st.session_state.current_inv_id is None else (
                list(inv_labels.values()).index(st.session_state.current_inv_id)
                if st.session_state.current_inv_id in inv_labels.values() else 0
            )
        )
        if st.button("Load Investigation", use_container_width=True):
            st.session_state.current_inv_id = inv_labels[current_selection]
            st.rerun()
    else:
        st.caption("No investigations executed yet. Launch one above!")


# ── Main Dashboard ─────────────────────────────────────────────────────────────
inv: Optional[Investigation] = None
if st.session_state.current_inv_id:
    inv = incident_engine.get_investigation(st.session_state.current_inv_id)

if not inv:
    # Landing / Overview View
    st.title("IncidentLens AI")
    st.markdown("### Autonomous Multi-Tool Production Outage Investigator")
    st.markdown("""
    IncidentLens AI diagnoses outages across CloudWatch telemetry, distributed logs, commit histories, and SOP runbooks:
    - **CloudWatch Telemetry & Metrics**: Latency (p50/p95/p99), error rates, CPU, memory, and database connection pools.
    - **Log Streams & Stack Traces**: Correlates exceptions and unhandled middleware failures.
    - **Deployment & Git Tracking**: Identifies code regressions, release diffs, and configuration drift.
    - **Ranked Hypotheses with Contradictory Evidence**: Weighs all evidence and computes calibrated confidence scores.
    - **Human-in-the-Loop Safe Remediation**: Safety guardrails require engineer authorization before executing any action.
    - **Automated Postmortem Reports**: Retrospective generation exportable to JSON, Markdown, and AWS S3.
    """)

    st.markdown("---")
    st.markdown("### ⚡ Pre-Configured Incident Scenarios Available")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        <div class="incident-card">
            <span class="badge-critical">Critical</span>
            <h4 style="margin-top: 8px;">API Deployment Regression</h4>
            <p style="font-size: 0.85rem; color: #94a3b8;">
                Unhandled timeout middleware regression in <code>api-2.4.1</code> triggering 18.4% 500 error rates on <code>api-gateway</code>.
            </p>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="incident-card">
            <span class="badge-critical">Critical</span>
            <h4 style="margin-top: 8px;">DB Connection Pool Exhaustion</h4>
            <p style="font-size: 0.85rem; color: #94a3b8;">
                Leaked database connections starving checkout endpoints on <code>order-processor</code> due to unindexed session query.
            </p>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div class="incident-card">
            <span class="badge-warning">High</span>
            <h4 style="margin-top: 8px;">Memory Pressure & GC Pauses</h4>
            <p style="font-size: 0.85rem; color: #94a3b8;">
                Heap exhaustion and 10s Stop-the-World GC pauses in <code>user-service</code> from a defective LRU cache eviction callback.
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.info("👈 Select a pre-configured incident scenario from the sidebar and click **🚀 Launch AI Investigation** to begin.")
    st.stop()


# ── Active Investigation Dashboard ─────────────────────────────────────────────
st.title(f"🔍 Incident Investigation: `{inv.service}`")

# Clear visual distinction between AI provider and Deterministic Scenario Mode (Requirement 7)
if inv.ai_provider_used == "bedrock":
    st.markdown("""
    <div class="mode-callout" style="background-color: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3);">
        <strong>🤖 AI Provider: Amazon Bedrock (Claude 3.5 Sonnet)</strong> — Real-time LLM evidence synthesis and root-cause reasoning across collected telemetry.
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div class="mode-callout" style="background-color: rgba(59, 130, 246, 0.1); border: 1px solid rgba(59, 130, 246, 0.3);">
        <strong>⚙️ Diagnostic Engine: Deterministic Scenario-Based Analysis</strong> — High-fidelity offline heuristic analysis (Zero External Cloud Credentials Required).
    </div>
    """, unsafe_allow_html=True)

st.caption(f"Investigation ID: `{inv.id}` | Created: `{inv.created_at}`")

# Status and Top KPI Row
m1, m2, m3, m4, m5 = st.columns(5)
with m1:
    status_label = inv.status.value.replace("_", " ").title()
    st.metric("Status", status_label)
with m2:
    st.metric("Target Service", inv.service)
with m3:
    st.metric("Evidence Items", len(inv.evidence))
with m4:
    top_hyp_title = inv.hypotheses[0].title if inv.hypotheses else "Analyzing..."
    st.metric("Leading Hypothesis", top_hyp_title[:20] + "...")
with m5:
    top_conf = inv.hypotheses[0].confidence.value.replace("_", " ").title() if inv.hypotheses else "Pending"
    st.metric("Confidence", top_conf)

st.markdown("---")

# Diagnostic Pipeline Stepper
st.markdown("### 🛠️ Diagnostic Agent Pipeline")
tool_cols = st.columns(len(inv.tool_history)) if inv.tool_history else [st.container()]
for idx, tool in enumerate(inv.tool_history):
    with tool_cols[idx]:
        if tool.status == ToolStatus.COMPLETED:
            st.markdown(f"**✅ {tool.display_name}**")
            st.caption(f"{tool.result_summary or 'Completed'} ({tool.evidence_count} evidence)")
        elif tool.status == ToolStatus.FAILED:
            st.markdown(f"**❌ {tool.display_name}**")
            st.caption(f"Failed: {tool.error}")
        else:
            st.markdown(f"**⏳ {tool.display_name}**")
            st.caption("Pending")

st.markdown("---")

# Main Content Tabs
tab_hypotheses, tab_remediation, tab_evidence, tab_report, tab_chat = st.tabs([
    "🎯 Ranked Hypotheses",
    "🛡️ Remediation & Guardrails",
    "📊 Evidence Explorer",
    "📝 Postmortem Report",
    "💬 SRE Assistant Q&A"
])

# ── Tab 1: Ranked Hypotheses ───────────────────────────────────────────────────
with tab_hypotheses:
    st.markdown("### 🏆 Root Cause Hypotheses (Ranked by Evidence)")
    if not inv.hypotheses:
        st.info("Hypothesis ranking is in progress or pending evidence correlation.")
    else:
        for hyp in inv.hypotheses:
            badge_html = get_confidence_badge_html(hyp.confidence)
            with st.container():
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

# ── Tab 2: Remediation & Guardrails (Human-in-the-Loop) ─────────────────────────
with tab_remediation:
    st.markdown("### 🛡️ Human-in-the-Loop Remediation")
    st.markdown(
        "IncidentLens AI enforces a strict safety boundary: **autonomous destructive actions or rollbacks "
        "will NEVER execute without explicit engineer sign-off**."
    )

    if not inv.remediation:
        st.info("No remediation action has been proposed yet.")
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

        st.markdown(f"**Automated Verification Plan:** `{rem.verification_procedure}`")

        # Remediation State Actions
        if rem.status == RemediationStatus.AWAITING_APPROVAL:
            c_app, c_rej, _ = st.columns([2, 2, 4])
            with c_app:
                if st.button("✅ Authorize & Execute Remediation", type="primary", use_container_width=True):
                    with st.spinner("Executing simulated remediation and running post-recovery verification..."):
                        run_coroutine(incident_engine.approve_remediation(inv.id, True))
                    st.success("Remediation executed and verified successfully!")
                    st.rerun()
            with c_rej:
                if st.button("❌ Reject Proposed Remediation", use_container_width=True):
                    run_coroutine(incident_engine.approve_remediation(inv.id, False))
                    st.warning("Remediation rejected by engineer.")
                    st.rerun()

        elif rem.status == RemediationStatus.COMPLETED:
            st.success(f"Remediation executed at `{rem.executed_at}`. Service recovery verified.")
            if inv.verification_result:
                ver = inv.verification_result
                st.markdown("#### 📈 Post-Remediation Verification Telemetry")
                
                # Metric comparison table
                v_df = pd.DataFrame([
                    {"Metric": k, "Before Remediation": str(v), "After Recovery": str(ver.after_metrics.get(k, "N/A"))}
                    for k, v in ver.before_metrics.items()
                ])
                st.dataframe(v_df, use_container_width=True, hide_index=True)

                st.markdown(f"**Verification Status:** `{'PASSED' if ver.passed else 'FAILED'}` | **Final System State:** `{ver.final_status}`")

        elif rem.status == RemediationStatus.REJECTED:
            st.error("Remediation was rejected by the engineer. System remains in diagnostic mode.")

# ── Tab 3: Evidence Explorer ───────────────────────────────────────────────────
with tab_evidence:
    st.markdown("### 📊 Correlated Diagnostic Evidence")
    
    # Telemetry before vs during incident
    scenario_meta = ALL_SCENARIOS.get(inv.scenario_id, {})
    if "metrics" in scenario_meta:
        with st.expander("📈 Baseline vs Incident Telemetry Metrics", expanded=True):
            pre_m = scenario_meta["metrics"].get("pre_incident", {})
            post_m = scenario_meta["metrics"].get("post_incident", {})
            metrics_rows = []
            for k in pre_m.keys():
                metrics_rows.append({
                    "Metric": k.replace("_", " ").title(),
                    "Pre-Incident Baseline": pre_m.get(k),
                    "During Incident": post_m.get(k),
                })
            st.dataframe(pd.DataFrame(metrics_rows), use_container_width=True, hide_index=True)

    ev_types = ["All"] + list(set(e.evidence_type for e in inv.evidence))
    selected_ev_type = st.selectbox("Filter Evidence Source", options=ev_types)

    filtered_evidence = [
        e for e in inv.evidence
        if selected_ev_type == "All" or e.evidence_type == selected_ev_type
    ]

    for item in filtered_evidence:
        sev_badge = "badge-critical" if item.severity in ("critical", "high") else (
            "badge-warning" if item.severity == "warning" else "badge-info"
        )
        with st.expander(f"[{item.evidence_type.upper()}] {item.summary[:100]}... (at {item.timestamp[11:19]})"):
            st.markdown(f"<span class='{sev_badge}'>{item.severity.upper()}</span> &nbsp; Source: <code>{item.source}</code>", unsafe_allow_html=True)
            st.markdown(f"**Finding:** {item.detail}")
            if item.raw:
                st.markdown("**Raw Telemetry / Payload:**")
                st.json(item.raw)

# ── Tab 4: Postmortem Report ───────────────────────────────────────────────────
with tab_report:
    st.markdown("### 📝 Incident Postmortem & Retrospective")
    if not inv.report:
        st.info("The formal postmortem report is automatically assembled once remediation and verification are completed.")
    else:
        rep = inv.report
        st.markdown(f"#### Executive Summary — `{rep.service}` Outage")
        st.markdown(f"**Impact:** {rep.impact_summary}")
        st.markdown(f"**Root Cause Assessment:** {rep.root_cause_assessment}")
        st.markdown(f"**Final Status:** `{rep.final_status}`")

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
        c_left, c_right = st.columns(2)
        with c_left:
            st.markdown("#### ✅ What Went Well")
            for w in rep.what_went_well:
                st.markdown(f"- {w}")
        with c_right:
            st.markdown("#### ⚠️ What Could Improve")
            for w in rep.what_could_improve:
                st.markdown(f"- {w}")

        st.markdown("---")
        st.markdown("#### 🎯 Follow-Up Action Items")
        for fa in rep.follow_up_actions:
            st.markdown(f"- **[{fa.get('priority', 'medium').upper()}]** {fa.get('action', '')} — *{fa.get('rationale', '')}*")

        st.markdown("---")
        col_d1, col_d2, _ = st.columns([2, 2, 4])
        with col_d1:
            md_content = format_report_to_markdown(rep)
            st.download_button(
                "📥 Download Markdown Report",
                data=md_content,
                file_name=f"postmortem_{inv.id[:8]}.md",
                mime="text/markdown",
                use_container_width=True
            )
        with col_d2:
            json_content = json.dumps(rep.model_dump(), indent=2, default=str)
            st.download_button(
                "📥 Download JSON Report",
                data=json_content,
                file_name=f"postmortem_{inv.id[:8]}.json",
                mime="application/json",
                use_container_width=True
            )

# ── Tab 5: SRE Assistant Q&A Chat ──────────────────────────────────────────────
with tab_chat:
    st.markdown("### 💬 Ask IncidentLens AI")
    st.caption("Interact with the investigation agent regarding root cause reasoning, contradictory evidence, and logs.")

    # Quick prompt buttons
    st.markdown("**Suggested Questions:**")
    qb1, qb2, qb3, qb4 = st.columns(4)
    quick_msg = None
    with qb1:
        if st.button("Why was this cause chosen?", use_container_width=True):
            quick_msg = "Why did you choose the leading root cause?"
    with qb2:
        if st.button("Contradictory evidence?", use_container_width=True):
            quick_msg = "What contradictory evidence was found?"
    with qb3:
        if st.button("Show log findings", use_container_width=True):
            quick_msg = "What were the key log findings?"
    with qb4:
        if st.button("Explain remediation", use_container_width=True):
            quick_msg = "What does the proposed remediation action do?"

    for chat_item in inv.chat_messages:
        role = chat_item.get("role", "assistant")
        with st.chat_message(role):
            st.markdown(chat_item.get("content", ""))

    user_query = st.chat_input("Ask a question about this incident...") or quick_msg
    if user_query:
        with st.chat_message("user"):
            st.markdown(user_query)

        with st.spinner("Analyzing incident context..."):
            ai_reply = run_coroutine(incident_engine.chat_with_investigation(inv.id, user_query))

        with st.chat_message("assistant"):
            st.markdown(ai_reply)
        st.rerun()
