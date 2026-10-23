"""
Tool: propose_remediation / execute_simulated_remediation / verify_recovery
"""
from datetime import datetime
from typing import Dict, Any, List
from app.data.scenarios.scenario_data import ALL_SCENARIOS
from app.models.investigation import RemediationProposal, RemediationResult, VerificationResult


def propose_remediation(scenario_id: str, hypothesis_id: str) -> RemediationProposal:
    scenario = ALL_SCENARIOS.get(scenario_id)
    if not scenario:
        raise ValueError(f"Scenario {scenario_id} not found")

    actions = scenario.get("remediation_actions", [])
    if not actions:
        raise ValueError(f"No remediation actions defined for scenario {scenario_id}")

    action = actions[0]  # Use the primary remediation action

    reason_map = {
        "scenario-deployment-regression": (
            "The leading hypothesis — deployment regression in api-2.4.1 — is strongly supported by temporal "
            "correlation and direct log evidence. Rolling back to api-2.4.0 removes the offending code change "
            "and is the lowest-risk path to service recovery."
        ),
        "scenario-db-connection-exhaustion": (
            "Connection pool exhaustion is strongly supported by explicit log evidence (100/100 connections active). "
            "Restarting the service releases all held connections and resets the pool to a healthy state, "
            "allowing requests to be served while the slow query is investigated."
        ),
        "scenario-memory-pressure": (
            "Memory pressure from a defective LRU cache eviction callback is the strongly supported root cause. "
            "Increasing the container memory limit is the fastest safe mitigation to stop OOM kills "
            "while the code fix is prepared and tested."
        ),
    }

    what_will_change_map = {
        "scenario-deployment-regression": "The api-gateway service will be switched to the api-2.4.0 image in the simulated environment. Traffic will briefly interrupt during the rollback (~30 s).",
        "scenario-db-connection-exhaustion": "The user-service process will be gracefully restarted. All active database connections will be closed and the pool reset. In-flight requests will fail during the ~5 s restart window.",
        "scenario-memory-pressure": "The container memory limit for order-processor will be updated from 512 MiB to 1 024 MiB in the simulated environment.",
    }

    return RemediationProposal(
        action_id=action["id"],
        action_type=action["type"],
        title=action["title"],
        description=action["description"],
        reason=reason_map.get(scenario_id, "Best available remediation based on investigation evidence."),
        expected_outcome=action["expected_outcome"],
        risks=action["risks"],
        what_will_change=what_will_change_map.get(scenario_id, "Simulated environment changes only."),
        verification_procedure="; ".join(action["verification"]),
    )


def execute_simulated_remediation(investigation_id: str, action_id: str, scenario_id: str) -> RemediationResult:
    """
    Executes the remediation action in the simulated environment only.
    Does NOT touch real infrastructure.
    """
    scenario = ALL_SCENARIOS.get(scenario_id)
    if not scenario:
        raise ValueError(f"Scenario {scenario_id} not found")

    changes_map = {
        "rollback-api-2.4.0": [
            "Switched api-gateway deployment from api-2.4.1 to api-2.4.0 (SIMULATED)",
            "Updated active container image in simulation state",
            "Health checks re-enabled — awaiting recovery confirmation",
        ],
        "restart-connection-pool": [
            "Graceful shutdown signal sent to user-service (SIMULATED)",
            "All 100 database connections released to pool",
            "Service restarted with fresh connection pool (0/100 active connections)",
        ],
        "scale-memory-limit": [
            "Container memory limit updated: 512 MiB → 1 024 MiB (SIMULATED)",
            "No OOM kill conditions active at new limit",
            "LRU cache eviction error flag noted for follow-up fix",
        ],
    }

    changes = changes_map.get(action_id, [f"Simulated action {action_id} executed"])

    return RemediationResult(
        action_id=action_id,
        status="completed",
        changes_applied=changes,
        timestamp=datetime.utcnow().isoformat(),
        environment="SIMULATED",
    )


def verify_recovery(investigation_id: str, scenario_id: str) -> VerificationResult:
    scenario = ALL_SCENARIOS.get(scenario_id)
    if not scenario:
        raise ValueError(f"Scenario {scenario_id} not found")

    resolution = scenario.get("resolution", {})
    pre = scenario["metrics"]["pre_incident"]
    post = scenario["metrics"]["post_incident"]

    # Simulate recovery metrics (close to pre-incident baseline with small variation)
    recovered = {
        "error_rate": round(pre["error_rate"] + 0.1, 2),
        "p95_latency_ms": pre["p95_latency_ms"] + 10,
        "availability": round(pre["availability"] - 0.02, 2),
        "memory_percent": round(pre["memory_percent"] - 2, 1),
        "connection_utilization": round(pre["connection_utilization"] - 4, 1),
    }

    checks_map = {
        "scenario-deployment-regression": [
            {"check": "Error rate < 1%", "before": f"{post['error_rate']}%", "after": f"{recovered['error_rate']}%", "passed": True},
            {"check": "P95 latency < 300 ms", "before": f"{post['p95_latency_ms']} ms", "after": f"{recovered['p95_latency_ms']} ms", "passed": recovered['p95_latency_ms'] < 300},
            {"check": "No new RequestProcessingError logs", "before": "Multiple", "after": "None", "passed": True},
            {"check": "Availability > 99%", "before": f"{post['availability']}%", "after": f"{recovered['availability']}%", "passed": recovered['availability'] > 99},
        ],
        "scenario-db-connection-exhaustion": [
            {"check": "Connection pool utilization < 60%", "before": f"{post['connection_utilization']}%", "after": f"{recovered['connection_utilization']}%", "passed": True},
            {"check": "Error rate < 1%", "before": f"{post['error_rate']}%", "after": f"{recovered['error_rate']}%", "passed": True},
            {"check": "No new ConnectionTimeoutError logs", "before": "Multiple", "after": "None", "passed": True},
            {"check": "P95 latency < 500 ms", "before": f"{post['p95_latency_ms']} ms", "after": f"{recovered['p95_latency_ms']} ms", "passed": True},
        ],
        "scenario-memory-pressure": [
            {"check": "No OOM kills in 10 min window", "before": "4 kills", "after": "0 kills", "passed": True},
            {"check": "Memory usage < 80% of new limit", "before": f"{post['memory_percent']}%", "after": f"{recovered['memory_percent']}%", "passed": True},
            {"check": "Error rate < 1%", "before": f"{post['error_rate']}%", "after": f"{recovered['error_rate']}%", "passed": True},
            {"check": "Service availability > 99%", "before": f"{post['availability']}%", "after": f"{recovered['availability']}%", "passed": True},
        ],
    }

    checks = checks_map.get(scenario_id, [
        {"check": "Service health restored", "before": "degraded", "after": "healthy", "passed": True}
    ])

    all_passed = all(c["passed"] for c in checks)
    resolution_passed = resolution.get("verification_passed", True)

    return VerificationResult(
        checks=checks,
        before_metrics={
            "error_rate": post["error_rate"],
            "p95_latency_ms": post["p95_latency_ms"],
            "availability": post["availability"],
            "memory_percent": post["memory_percent"],
            "connection_utilization": post["connection_utilization"],
        },
        after_metrics=recovered,
        passed=all_passed and resolution_passed,
        remaining_issues=[] if all_passed else ["Some verification checks did not pass"],
        final_status="resolved" if (all_passed and resolution_passed) else "partially_resolved",
    )
