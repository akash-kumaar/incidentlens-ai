# IncidentLens AI

> **Autonomous Agentic Production Incident Investigator**  
> Diagnoses outages across CloudWatch telemetry, logs, traces, code changes, and runbooks with ranked hypotheses, human-in-the-loop remediation, and automated postmortems.

---

## Architecture Overview

```
                      ┌────────────────────────────────────────┐
                      │          React 19 + Vite UI            │
                      │  (Tailwind CSS, Lucide, Recharts)      │
                      └──────────────────┬─────────────────────┘
                                         │ REST API
                                         ▼
                      ┌────────────────────────────────────────┐
                      │          FastAPI Backend Engine        │
                      └─────┬────────────┬─────────────┬───────┘
                            │            │             │
        ┌───────────────────┴──┐   ┌─────┴───────┐   ┌─┴──────────────────┐
        │  Investigation Tools │   │ AI Provider │   │  Storage & Report  │
        │  - CloudWatch Metrics│   │ - Bedrock   │   │  - JSON / Markdown │
        │  - Log Insights      │   │   (Claude)  │   │  - AWS S3 Cold     │
        │  - Distributed Traces│   │ - Local     │   │    Archive         │
        │  - Canary / Deploy   │   │   Engine    │   │                    │
        │  - Runbook Retrieval │   │             │   │                    │
        └──────────────────────┘   └─────────────┘   └────────────────────┘
```

---

## Key Features

1. **Minimal, Developer-Centric UI**:
   - Zero dashboard clutter. Follows progressive disclosure and high-signal presentation.
   - Live telemetry status indicator and AI connection badge.

2. **Autonomous Multi-Tool Diagnostics**:
   - **Metrics Analyzer**: Anomaly detection across latency (p50/p95/p99), error rates, CPU, and memory.
   - **Log Investigator**: Stack trace parsing, error pattern clustering, and log correlation.
   - **Trace Inspector**: Distributed trace bottleneck analysis and upstream/downstream dependency mapping.
   - **Deployment Tracker**: Git commit diffs, release tags, and configuration drift detection.
   - **Runbook Matcher**: Operational standard operating procedure (SOP) verification and remediation recommendation.

3. **Ranked Hypotheses & Confidence Scoring**:
   - Evaluates evidence as *Supporting*, *Contradictory*, or *Neutral*.
   - Confidence categories: `Strongly Supported`, `Plausible`, `Weakly Supported`, `Insufficient Evidence`.

4. **Human-in-the-Loop Remediation**:
   - Safety guardrail: Autonomous rollbacks or parameter adjustments require explicit engineer approval.
   - Pre-remediation blast radius preview and post-remediation health verification.

5. **Automated Postmortem Generation & S3 Archival**:
   - Generates complete retrospective reports including root cause, timeline, what went well, what could improve, and follow-up preventive actions.
   - Exports to JSON and Markdown; supports optional direct archival to AWS S3.

---

## Pre-Seeded Incident Scenarios

IncidentLens AI is pre-configured with 3 realistic production incident scenarios:

1. **API Deployment Regression** (`api-gateway`):
   - Sudden spike in 500 error rates and p99 latency after release `api-2.4.1` with unhandled timeout middleware.
2. **Database Connection Pool Exhaustion** (`order-processor`):
   - Leaked connection pool starving downstream checkout endpoints, accompanied by slow query execution spikes.
3. **Memory Pressure & Garbage Collection Pauses** (`user-service`):
   - Heap memory exhaustion triggering frequent Stop-the-World GC pauses, causing intermittent health check timeouts.

---

## Tech Stack

- **Backend**: Python 3.10+, FastAPI, Pydantic v2, Uvicorn, Boto3, HTTPX, Pytest
- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS, Recharts, Lucide Icons, Axios

---

## Prerequisites

- **Python**: 3.10 or higher
- **Node.js**: 18.0.0 or higher (with npm)
- **Git**

---

## Quick Start

### 1. Backend Setup

```bash
cd backend

# Create virtual environment (optional but recommended)
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Windows (CMD):
.\venv\Scripts\activate.bat
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start backend dev server
uvicorn app.main:app --reload --port 8000
```

- Backend API: `http://localhost:8000`
- Interactive Swagger API docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/api/health`

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start Vite dev server
npm run dev
```

- Frontend UI: `http://localhost:5173`

---

## Configuration & Environment Variables

Copy `.env.example` to `backend/.env` to configure optional integrations:

```bash
cp .env.example backend/.env
```

| Variable | Default | Description |
|---|---|---|
| `APP_NAME` | `IncidentLens AI` | Application name |
| `VERSION` | `1.0.0` | API version |
| `DEBUG` | `false` | Enable verbose debug logging |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | Allowed CORS origin |
| `AI_PROVIDER` | `local` | `local` (built-in deterministic simulator) or `bedrock` (Amazon Bedrock) |
| `AWS_REGION` | `us-east-1` | AWS region for Bedrock and S3 |
| `BEDROCK_MODEL_ID` | `anthropic.claude-3-sonnet-20240229-v1:0` | Amazon Bedrock foundation model ID |
| `S3_BUCKET` | *None* | Optional S3 bucket name for archiving postmortem reports |
| `S3_REPORTS_PREFIX` | `incidentlens/reports/` | S3 key prefix for archived reports |
| `AWS_ACCESS_KEY_ID` | *None* | Optional AWS Access Key (prefer IAM roles or AWS CLI credentials) |
| `AWS_SECRET_ACCESS_KEY` | *None* | Optional AWS Secret Key (prefer IAM roles or AWS CLI credentials) |

### Demo / Local Mode (Default)
When `AI_PROVIDER=local`, IncidentLens AI functions entirely offline with zero external dependencies. In this mode, telemetry, logs, traces, runbook matches, hypothesis generation, and verification are evaluated deterministically using pre-configured incident scenarios.

### Cloud / Bedrock Mode (Optional)
When `AI_PROVIDER=bedrock`, the backend leverages Amazon Bedrock (Claude) to synthesize hypotheses and answer investigation questions in real-time. Ensure your AWS credentials have `bedrock:InvokeModel` and `bedrock:ListFoundationModels` permissions.

---

## Testing & Quality Assurance

### Run Backend Tests
```bash
cd backend
python -m pytest
```

### Run Frontend Typecheck & Build
```bash
cd frontend
npm run build
```

### Run Frontend Linter
```bash
cd frontend
npm run lint
```

---

## Known Limitations

- **Simulated Scenarios**: In `local` mode, telemetry and logs are sourced from deterministic test datasets representing real incident patterns.
- **Remediation Guardrail**: All remediation actions are staged for human-in-the-loop review; in simulated mode, remediation executes against in-memory mock service states.
- **AWS Permissions**: Enabling `bedrock` or `s3` requires appropriate AWS IAM credentials configured either via environment variables, `~/.aws/credentials`, or instance roles.

---

## License

MIT License. See [LICENSE](LICENSE) for details.
