# IncidentLens AI — System Architecture

IncidentLens AI is an autonomous, agentic production incident investigation platform designed for SRE and DevOps teams.

## High-Level Architecture

The system is structured as a decoupled full-stack application:

- **Frontend**: React 19 Single Page Application (SPA) powered by Vite, Tailwind CSS, Lucide icons, and Recharts for responsive telemetry visualization.
- **Backend Engine**: FastAPI ASGI service orchestrating data ingestion, multi-tool diagnostics, hypothesis generation, human-in-the-loop remediation, and automated postmortem reporting.
- **AI / Reasoning Layer**: Dual-mode engine supporting deterministic rule-based local simulation or real-time reasoning via Amazon Bedrock (Anthropic Claude).

---

## Multi-Tool Diagnostic Pipeline

When an incident investigation starts, the agent coordinates across specialized diagnostic tools:

1. **Metrics Inspector** (`inspect_metrics.py`):
   - Computes baseline statistical models for latency (p50, p95, p99), error rates, CPU, and memory.
   - Detects metric anomalies against pre-incident operating windows.

2. **Log Investigator** (`inspect_logs.py`):
   - Aggregates service logs and filters by severity (ERROR, CRITICAL, WARN).
   - Extracts stack traces, categorizes unhandled exceptions, and clusters error patterns.

3. **Trace Inspector** (`inspect_service_health.py`):
   - Traces requests across upstream and downstream service dependencies.
   - Maps service graphs and isolates bottleneck components.

4. **Deployment Tracker** (`inspect_deployments.py`):
   - Correlates incident onset times with Git commits, deployments, and configuration releases.
   - Identifies candidate breaking changes and code regressions.

5. **Evidence Correlator & Hypothesis Ranker** (`correlate_evidence.py`, `rank_hypotheses.py`):
   - Weighs all collected artifacts into supporting, contradictory, or neutral evidence sets.
   - Computes confidence scores: `Strongly Supported`, `Plausible`, `Weakly Supported`, `Insufficient Evidence`.

---

## Human-in-the-Loop Remediation & Safety Guardrail

Remediation actions (e.g. rolling back deployments, restarting services, scaling resource allocations) are strictly guarded:
- The agent drafts the remediation plan with blast-radius estimation and expected outcomes.
- An engineer reviews the proposal and explicitly approves or rejects the action via the UI or API.
- Upon approval, the remediation executes, followed by automated verification checks to ensure health restoration.

---

## Postmortem Generation & S3 Archival

Once recovery is verified:
- The engine compiles a comprehensive retrospective postmortem including executive summary, incident timeline, root cause analysis, what went well, what could improve, and prioritized follow-up items.
- The report can be downloaded directly as JSON or Markdown, and optionally archived to an AWS S3 bucket for audit compliance.
