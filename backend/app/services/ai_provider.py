"""
Service: AI Provider abstraction (local simulation + Amazon Bedrock)
"""
import json
import logging
from typing import Dict, Any, Optional
from app.config import settings

logger = logging.getLogger(__name__)


class LocalAIProvider:
    """Deterministic local provider — does not call any external service."""

    def analyze_evidence(self, evidence: Dict[str, Any], scenario_id: str) -> Dict[str, Any]:
        return {
            "provider": "local_simulation",
            "summary": self._local_summary(scenario_id),
            "key_observations": self._local_observations(scenario_id),
            "uncertainty": self._local_uncertainty(scenario_id),
            "recommended_next_step": self._local_next_step(scenario_id),
        }

    def _local_summary(self, scenario_id: str) -> str:
        m = {
            "scenario-deployment-regression": (
                "The collected evidence strongly suggests a code regression introduced in api-2.4.1. "
                "The temporal correlation between the deployment and the error onset is tight, and the "
                "log evidence directly implicates the modified RequestMiddleware."
            ),
            "scenario-db-connection-exhaustion": (
                "Evidence points to database connection pool exhaustion as the primary cause. "
                "The pool reached 100% utilization due to slow queries on the user_sessions table "
                "holding connections open longer than expected."
            ),
            "scenario-memory-pressure": (
                "A defective LRU cache eviction callback introduced in order-processor-2.2.0 is "
                "causing a memory leak. The container is being OOM-killed every ~7 minutes, "
                "causing intermittent unavailability."
            ),
        }
        return m.get(scenario_id, "Evidence collected. Review hypotheses for details.")

    def _local_observations(self, scenario_id: str) -> list:
        m = {
            "scenario-deployment-regression": [
                "OBSERVED FACT: Deployment api-2.4.1 completed at 13:45 UTC.",
                "OBSERVED FACT: Error rate rose from 0.4% to 18.4% at 13:48 UTC (3 min after deployment).",
                "OBSERVED FACT: Log entries show NullPointerException in RequestMiddleware.process() line 247.",
                "INTERPRETATION: The exception is in code modified by api-2.4.1, suggesting the change introduced a null-reference bug.",
            ],
            "scenario-db-connection-exhaustion": [
                "OBSERVED FACT: Connection pool utilization reached 98.4% (effectively full).",
                "OBSERVED FACT: Logs confirm 100/100 connections active — new requests cannot acquire a connection.",
                "OBSERVED FACT: A slow query on user_sessions took 42 seconds — well above acceptable thresholds.",
                "INTERPRETATION: The slow query is holding connections open, causing pool saturation over time.",
            ],
            "scenario-memory-pressure": [
                "OBSERVED FACT: Container memory usage grew from 62% to 97%+ in repeating ~7-minute cycles.",
                "OBSERVED FACT: OOM kill events occurred 4 times in 30 minutes.",
                "OBSERVED FACT: LRU cache eviction callback raised AttributeError — items not freed correctly.",
                "INTERPRETATION: The eviction bug prevents the cache from releasing memory, causing a memory leak.",
            ],
        }
        return m.get(scenario_id, ["No specific observations available."])

    def _local_uncertainty(self, scenario_id: str) -> str:
        m = {
            "scenario-deployment-regression": "Temporal correlation does not prove causation. A code diff review of RequestMiddleware is required to confirm.",
            "scenario-db-connection-exhaustion": "The immediate cause is confirmed (pool exhausted), but whether the root cause is the slow query or a connection leak requires further investigation.",
            "scenario-memory-pressure": "The eviction error is strongly implicated but a heap dump is required to confirm which object type is accumulating.",
        }
        return m.get(scenario_id, "Uncertainty level: moderate. Further evidence required.")

    def _local_next_step(self, scenario_id: str) -> str:
        m = {
            "scenario-deployment-regression": "Review the proposed rollback to api-2.4.0 and approve if you agree the evidence supports it.",
            "scenario-db-connection-exhaustion": "Approve the service restart to reset the connection pool, then investigate the slow query.",
            "scenario-memory-pressure": "Approve the memory limit increase to stop OOM kills, then schedule a fix for the eviction callback.",
        }
        return m.get(scenario_id, "Review the hypotheses and approve the proposed remediation action.")

    def chat_response(self, message: str, investigation_context: Dict[str, Any]) -> str:
        msg = message.lower()
        scenario_id = investigation_context.get("scenario_id", "")
        hyps = investigation_context.get("hypotheses", [])

        if any(w in msg for w in ["why", "cause", "root cause", "hypothesis"]):
            if hyps:
                top = hyps[0]
                return (
                    f"The leading hypothesis is: **{top.get('title', 'Unknown')}**.\n\n"
                    f"Confidence: {top.get('confidence', 'unknown').replace('_', ' ').title()}.\n\n"
                    f"Key supporting evidence:\n" +
                    "\n".join(f"• {e}" for e in top.get("supporting_evidence", [])[:3]) +
                    f"\n\nUncertainty: {top.get('contradictory_evidence', ['None noted'])[0] if top.get('contradictory_evidence') else 'None noted'}."
                )
            return "Investigation is still in progress. Check back once evidence collection is complete."

        if any(w in msg for w in ["contradiction", "contradict", "against", "doubt"]):
            if hyps:
                top = hyps[0]
                contra = top.get("contradictory_evidence", [])
                if contra:
                    return "**Contradictory evidence:**\n" + "\n".join(f"• {e}" for e in contra)
            return "No significant contradictory evidence has been identified for the leading hypothesis."

        if any(w in msg for w in ["next", "what should", "recommend", "do next"]):
            rem = investigation_context.get("remediation")
            if rem:
                return f"The recommended next step is to review and approve the proposed remediation: **{rem.get('title', 'review remediation')}**."
            return "Once evidence collection and hypothesis ranking are complete, a remediation proposal will be generated for your review."

        if any(w in msg for w in ["log", "logs", "error", "exception"]):
            evidence = investigation_context.get("evidence", [])
            log_evidence = [e for e in evidence if e.get("evidence_type") == "log"]
            if log_evidence:
                top_log = log_evidence[0]
                return f"Most relevant log finding:\n\n```\n{top_log.get('detail', top_log.get('summary', 'No detail available'))}\n```"
            return "Log evidence has not been collected yet, or no relevant log entries were found."

        if any(w in msg for w in ["deploy", "deployment", "release", "version"]):
            evidence = investigation_context.get("evidence", [])
            dep_evidence = [e for e in evidence if e.get("evidence_type") == "deployment"]
            if dep_evidence:
                d = dep_evidence[0]
                return f"**Deployment finding:**\n\n{d.get('detail', d.get('summary', 'No deployment details available'))}"
            return "Deployment data has not been collected yet."

        if any(w in msg for w in ["rollback", "restart", "fix", "remediat", "approve"]):
            rem = investigation_context.get("remediation")
            if rem:
                return (
                    f"**Proposed remediation:** {rem.get('title')}\n\n"
                    f"**Reason:** {rem.get('reason')}\n\n"
                    f"**Expected outcome:** {rem.get('expected_outcome')}\n\n"
                    f"To proceed, use the 'Review Remediation' button in the investigation panel and approve the action."
                )
            return "No remediation has been proposed yet. Complete the investigation first."

        if any(w in msg for w in ["postmortem", "report", "summary"]):
            return (
                "The postmortem report will be generated automatically once recovery is verified. "
                "It will include the incident timeline, root-cause assessment, resolution steps, and follow-up actions."
            )

        if any(w in msg for w in ["verify", "verification", "recover", "resolved"]):
            ver = investigation_context.get("verification_result")
            if ver:
                status = "passed" if ver.get("passed") else "failed"
                return f"Verification {status}. Final status: {ver.get('final_status', 'unknown')}."
            return "Verification has not been run yet. Approve the remediation action to proceed."

        return (
            "I'm IncidentLens AI, your investigation assistant. I can answer questions about:\n"
            "• The root cause and supporting evidence\n"
            "• Contradictory evidence\n"
            "• Deployment changes\n"
            "• Log findings\n"
            "• The proposed remediation and what it will do\n"
            "• Verification results\n\n"
            "What would you like to know?"
        )


class BedrockAIProvider:
    """Real Amazon Bedrock provider using Claude."""

    def __init__(self):
        self._client = None
        self._available = False
        self._error = None
        self._try_init()

    def _try_init(self):
        try:
            import boto3
            from botocore.exceptions import NoCredentialsError, ClientError
            client = boto3.client("bedrock-runtime", region_name=settings.aws_region)
            # Quick connectivity test — list foundation models
            bedrock_client = boto3.client("bedrock", region_name=settings.aws_region)
            bedrock_client.list_foundation_models(byProvider="Anthropic")
            self._client = client
            self._available = True
            logger.info("Bedrock provider initialized successfully.")
        except Exception as e:
            self._available = False
            self._error = str(e)
            logger.warning(f"Bedrock unavailable: {e}")

    @property
    def available(self) -> bool:
        return self._available

    @property
    def error(self) -> Optional[str]:
        return self._error

    def _invoke(self, prompt: str) -> str:
        if not self._client:
            raise RuntimeError("Bedrock client not initialized")
        import json
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
        })
        response = self._client.invoke_model(
            modelId=settings.bedrock_model_id,
            body=body,
            contentType="application/json",
            accept="application/json",
        )
        result = json.loads(response["body"].read())
        return result["content"][0]["text"]

    def analyze_evidence(self, evidence: Dict[str, Any], scenario_id: str) -> Dict[str, Any]:
        if not self._available:
            raise RuntimeError(f"Bedrock not available: {self._error}")

        prompt = (
            "You are IncidentLens AI, an expert incident investigator. "
            "You have been provided with evidence collected from production monitoring tools. "
            "Analyze the evidence and return a JSON object with these exact fields:\n"
            "- summary: a concise 2-3 sentence summary of what the evidence shows\n"
            "- key_observations: list of strings, each labeled as OBSERVED FACT or INTERPRETATION\n"
            "- uncertainty: a sentence describing what remains uncertain\n"
            "- recommended_next_step: one specific recommended action\n\n"
            "IMPORTANT: Only reference evidence actually provided. Do not invent log entries, metrics, or deployment events.\n\n"
            f"Evidence:\n{json.dumps(evidence, indent=2)}\n\n"
            "Return only valid JSON."
        )

        try:
            raw = self._invoke(prompt)
            # Extract JSON from response
            start = raw.find("{")
            end = raw.rfind("}") + 1
            result = json.loads(raw[start:end])
            result["provider"] = "amazon_bedrock"
            result["model"] = settings.bedrock_model_id
            return result
        except Exception as e:
            logger.error(f"Bedrock response parsing failed: {e}")
            raise RuntimeError(f"Bedrock response invalid: {e}")

    def chat_response(self, message: str, investigation_context: Dict[str, Any]) -> str:
        if not self._available:
            raise RuntimeError(f"Bedrock not available: {self._error}")

        context_str = json.dumps({
            "scenario_id": investigation_context.get("scenario_id"),
            "service": investigation_context.get("service"),
            "status": investigation_context.get("status"),
            "top_hypothesis": investigation_context.get("hypotheses", [{}])[0] if investigation_context.get("hypotheses") else {},
            "remediation_status": investigation_context.get("remediation", {}).get("status") if investigation_context.get("remediation") else None,
        }, indent=2)

        prompt = (
            "You are IncidentLens AI assistant. You are helping a developer investigate a production incident.\n"
            "Answer the user's question using only the information in the investigation context below.\n"
            "Do not invent evidence. If you don't know something from the context, say so.\n"
            "Keep your answer concise and technical.\n\n"
            f"Investigation context:\n{context_str}\n\n"
            f"User question: {message}\n\n"
            "Answer:"
        )

        return self._invoke(prompt)


def get_ai_provider():
    """Returns the configured provider; falls back to local on failure."""
    if settings.ai_provider == "bedrock":
        provider = BedrockAIProvider()
        if provider.available:
            return provider, "amazon_bedrock"
        logger.warning(f"Bedrock unavailable, falling back to local: {provider.error}")
    return LocalAIProvider(), "local_simulation"
