"""
Tool: correlate_evidence
Builds a temporal correlation map from collected evidence.
"""
from typing import List, Dict, Any


def correlate_evidence(
    health_data: Dict[str, Any],
    log_data: Dict[str, Any],
    metrics_data: Dict[str, Any],
    deployment_data: Dict[str, Any],
    scenario_id: str,
) -> Dict[str, Any]:
    correlated_events = []
    supporting = []
    contradictory = []
    missing = []

    # Build event sequence
    if deployment_data.get("most_recent_deployment"):
        dep = deployment_data["most_recent_deployment"]
        correlated_events.append({
            "timestamp": dep.get("timestamp"),
            "event": f"Deployment {dep.get('version')} — {dep.get('change_summary', '')[:80]}",
            "type": "deployment",
        })

    for log in log_data.get("log_entries", [])[:3]:
        correlated_events.append({
            "timestamp": log.get("timestamp"),
            "event": f"[{log.get('level')}] {log.get('message', '')[:100]}",
            "type": "log",
        })

    correlated_events.sort(key=lambda x: x.get("timestamp", ""))

    # Scenario-specific correlation logic
    if "deployment-regression" in scenario_id:
        supporting = [
            "Deployment api-2.4.1 occurred 35 minutes before error rate spike",
            "Error rate increased from 0.4% to 18.4% immediately post-deployment",
            "Log entries show RequestProcessingError in code modified by api-2.4.1",
            "P95 latency degraded from 180 ms to 4 800 ms concurrently",
        ]
        contradictory = [
            "Health check endpoint (/health) continued returning 200 OK — partial failure, not total outage",
            "CPU and memory remain within normal bounds — not a resource saturation issue",
        ]
        missing = [
            "A/B traffic split data to isolate whether all replicas are affected",
            "Code diff for the specific middleware change in api-2.4.1",
        ]
        temporal_summary = (
            "Strong temporal correlation: degradation began within 3 minutes of deployment completion. "
            "Log evidence directly implicates code modified in api-2.4.1."
        )

    elif "db-connection" in scenario_id:
        supporting = [
            "Connection pool utilization climbed from 42% baseline to 98.4%",
            "Logs explicitly report pool exhausted (100/100 connections active)",
            "Slow query detected on user_sessions — holding connections open longer",
            "Error rate correlates with pool exhaustion timeline",
        ]
        contradictory = [
            "Deployment occurred 24 hours before incident — weak temporal link",
            "CPU and memory normal — compute is not the constraint",
        ]
        missing = [
            "Database query execution plan for the new session analytics query",
            "Pool configuration history to check if max_connections was recently reduced",
        ]
        temporal_summary = (
            "Moderate temporal correlation: pool exhaustion developed gradually over 45 minutes. "
            "Slow queries appear to be holding connections open longer than expected."
        )

    elif "memory-pressure" in scenario_id:
        supporting = [
            "Memory usage climbed from 62% to 97%+ before each OOM kill",
            "OOM kills follow a repeating pattern every ~7 minutes",
            "LRU cache eviction error logged — items not being freed",
            "Deployment 2.2.0 introduced LRU cache feature 2 hours before incident",
        ]
        contradictory = [
            "CPU usage remains within normal bounds — not CPU pressure",
            "Request rate is within normal parameters — not a traffic spike",
        ]
        missing = [
            "Heap dump or memory profiling output from the container",
            "LRU cache configuration (max size, TTL, eviction policy)",
        ]
        temporal_summary = (
            "Clear causal pattern: memory leak cycle confirmed by repeated OOM kills. "
            "Deployment 2.2.0 correlates temporally; LRU cache eviction error in logs directly implicates the feature."
        )
    else:
        temporal_summary = "Evidence correlation complete."

    return {
        "correlated_events": correlated_events,
        "temporal_summary": temporal_summary,
        "supporting_evidence": supporting,
        "contradictory_evidence": contradictory,
        "missing_information": missing,
        "correlation_strength": _correlation_strength(scenario_id),
    }


def _correlation_strength(scenario_id: str) -> str:
    if "deployment-regression" in scenario_id:
        return "strong"
    elif "memory-pressure" in scenario_id:
        return "strong"
    elif "db-connection" in scenario_id:
        return "moderate"
    return "weak"
