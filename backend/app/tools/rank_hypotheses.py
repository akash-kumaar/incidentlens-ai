"""
Tool: rank_hypotheses
Ranks candidate root-cause hypotheses using transparent scoring rules.
"""
from typing import List, Dict, Any
from app.models.investigation import Hypothesis, ConfidenceCategory


def rank_hypotheses(correlation_result: Dict[str, Any], scenario_id: str) -> List[Hypothesis]:
    """
    Produces scenario-specific hypotheses ranked by confidence.
    Confidence categories follow transparent rules:
      - Strongly Supported: multiple independent evidence types confirm; clear temporal link
      - Plausible: consistent evidence but one or more alternative explanations remain
      - Weakly Supported: some evidence fits but major gaps exist
      - Insufficient Evidence: too little data to evaluate
    """
    if "deployment-regression" in scenario_id:
        return [
            Hypothesis(
                id="hyp-001",
                title="Deployment Regression: api-2.4.1 middleware change",
                rank=1,
                confidence=ConfidenceCategory.STRONGLY_SUPPORTED,
                confidence_explanation=(
                    "Strongly supported: temporal correlation is tight (errors began within 3 min of deployment), "
                    "logs directly reference code modified in this release, and no alternative resource anomaly was found."
                ),
                supporting_evidence=[
                    "Deployment api-2.4.1 completed 35 min before error onset",
                    "RequestProcessingError NullPointerException at RequestMiddleware.process() line 247 (code path modified in api-2.4.1)",
                    "Error rate jumped from 0.4% to 18.4% immediately post-deployment",
                    "P95 latency degraded from 180 ms to 4 800 ms at same time",
                ],
                contradictory_evidence=[
                    "Health check endpoint continued returning 200 OK — not a total failure",
                    "CPU and memory within baseline — resource exhaustion not the primary driver",
                ],
                missing_evidence=[
                    "Code diff for the specific middleware change",
                    "Traffic split data to confirm all replicas are affected",
                ],
                recommended_verification="Compare api-2.4.1 change diff for RequestMiddleware.process() against line 247",
                recommended_action="Roll back to api-2.4.0 and verify error rate recovery",
            ),
            Hypothesis(
                id="hyp-002",
                title="Upstream dependency failure",
                rank=2,
                confidence=ConfidenceCategory.WEAKLY_SUPPORTED,
                confidence_explanation=(
                    "Weakly supported: circuit breaker opened against a downstream service, but the primary error "
                    "pattern implicates a code exception rather than a network failure."
                ),
                supporting_evidence=[
                    "Circuit breaker OPEN log entry observed — downstream service unavailable after 10 failures",
                ],
                contradictory_evidence=[
                    "Error pattern (NullPointerException in local middleware) precedes circuit breaker opening",
                    "Errors began immediately at deployment, not gradually as expected from dependency failure",
                ],
                missing_evidence=[
                    "Downstream service health metrics",
                    "Network trace data",
                ],
                recommended_verification="Check downstream service health dashboard and trace IDs",
                recommended_action="Investigate downstream service health before ruling out as contributing factor",
            ),
        ]

    elif "db-connection" in scenario_id:
        return [
            Hypothesis(
                id="hyp-001",
                title="Database Connection Pool Exhaustion",
                rank=1,
                confidence=ConfidenceCategory.STRONGLY_SUPPORTED,
                confidence_explanation=(
                    "Strongly supported: pool utilization reached 100%, logs explicitly confirm 100/100 active connections, "
                    "and error timeline directly follows pool saturation."
                ),
                supporting_evidence=[
                    "Pool utilization reached 98.4% (effectively full)",
                    "ConnectionTimeoutError: pool exhausted (100/100 connections active) — explicit log evidence",
                    "Slow query on user_sessions table holding connections open longer than expected",
                    "Error rate onset precisely tracks pool saturation timeline",
                ],
                contradictory_evidence=[
                    "CPU and memory are within normal bounds — this is not compute saturation",
                    "Deployment was 24 hours prior — weak direct causal link",
                ],
                missing_evidence=[
                    "Query execution plan for new session analytics query",
                    "Historical pool utilization trend to detect gradual leak vs spike",
                ],
                recommended_verification="Run SHOW PROCESSLIST on the database to see long-running queries",
                recommended_action="Restart the service to reset pool and investigate slow query with EXPLAIN ANALYZE",
            ),
            Hypothesis(
                id="hyp-002",
                title="Missing database index on user_sessions table",
                rank=2,
                confidence=ConfidenceCategory.PLAUSIBLE,
                confidence_explanation=(
                    "Plausible: slow query log explicitly references user_sessions with suspected missing index. "
                    "This may be the root cause of connections being held open."
                ),
                supporting_evidence=[
                    "Slow query log: 'SELECT * FROM user_sessions ... took 42 s — missing index suspected'",
                    "New deployment added queries to user_sessions table",
                ],
                contradictory_evidence=[
                    "Table existed before the new deployment — index absence would have been noticed earlier",
                ],
                missing_evidence=[
                    "EXPLAIN ANALYZE output for the problematic query",
                    "Database index list for user_sessions",
                ],
                recommended_verification="Run EXPLAIN ANALYZE on the slow query; review table indexes",
                recommended_action="Add index on user_sessions.last_active if missing after restart",
            ),
        ]

    elif "memory-pressure" in scenario_id:
        return [
            Hypothesis(
                id="hyp-001",
                title="Memory Leak in LRU Cache (order-processor-2.2.0)",
                rank=1,
                confidence=ConfidenceCategory.STRONGLY_SUPPORTED,
                confidence_explanation=(
                    "Strongly supported: LRU cache eviction error explicitly logged, "
                    "memory grows to 97%+ every ~7 minutes, OOM kill pattern is consistent, "
                    "and the cache feature was introduced in the deployment 2 hours before incident."
                ),
                supporting_evidence=[
                    "LRU cache eviction callback raised AttributeError — items not being freed",
                    "Memory grows from ~62% to 97%+ in a consistent ~7-minute cycle",
                    "Deployment order-processor-2.2.0 added LRU caching 2 hours before incident",
                    "OOM kills repeated 4 times — confirms a repeating leak, not a one-time spike",
                ],
                contradictory_evidence=[
                    "Request rate is within normal bounds — traffic is not the driver",
                    "CPU remains normal — this is not a compute-bound issue",
                ],
                missing_evidence=[
                    "Heap dump to identify which objects are accumulating",
                    "LRU cache max-size and TTL configuration",
                ],
                recommended_verification="Obtain heap dump; check LRU cache size and eviction callback implementation",
                recommended_action="Increase memory limit as immediate mitigation; fix eviction callback in next release",
            ),
            Hypothesis(
                id="hyp-002",
                title="Insufficient container memory limit",
                rank=2,
                confidence=ConfidenceCategory.PLAUSIBLE,
                confidence_explanation=(
                    "Plausible contributing factor: the container memory limit of 512 MiB may be too low for the "
                    "new caching feature's workload even under correct eviction. However, the leak pattern "
                    "suggests a bug rather than simply a too-small limit."
                ),
                supporting_evidence=[
                    "Memory limit: 512 MiB — tight for an application with an in-memory LRU cache",
                    "Increasing the limit is the recommended immediate remediation",
                ],
                contradictory_evidence=[
                    "Eviction error in logs strongly suggests a software bug is the root cause",
                    "Pre-incident memory usage was only 62% — the limit was not a problem before 2.2.0",
                ],
                missing_evidence=[
                    "Expected cache size under normal traffic",
                ],
                recommended_verification="Compare expected cache size at steady state against container limit",
                recommended_action="Increase limit as short-term fix; prioritize eviction bug fix in code",
            ),
        ]

    # Generic fallback
    return [
        Hypothesis(
            id="hyp-001",
            title="Unknown root cause",
            rank=1,
            confidence=ConfidenceCategory.INSUFFICIENT_EVIDENCE,
            confidence_explanation="Insufficient evidence to determine root cause. Further investigation required.",
            supporting_evidence=[],
            contradictory_evidence=[],
            missing_evidence=["More diagnostic data required"],
            recommended_verification="Collect additional metrics and logs",
            recommended_action="Gather more evidence before taking action",
        )
    ]
