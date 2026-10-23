"""
Tool: inspect_service_health
Returns health metrics for a given service and time window.
"""
from datetime import datetime
from typing import Dict, Any
from app.data.scenarios.scenario_data import ALL_SCENARIOS, SERVICES


def inspect_service_health(service_id: str, scenario_id: str, time_window_minutes: int = 60) -> Dict[str, Any]:
    scenario = ALL_SCENARIOS.get(scenario_id)
    service = SERVICES.get(service_id, {})

    if not scenario:
        return {"error": f"Scenario {scenario_id} not found", "service_id": service_id}

    metrics_pre = scenario["metrics"]["pre_incident"]
    metrics_post = scenario["metrics"]["post_incident"]

    return {
        "service_id": service_id,
        "service_name": service.get("name", service_id),
        "status": "degraded" if metrics_post["error_rate"] > 5 else "healthy",
        "availability_percent": metrics_post["availability"],
        "request_rate_rps": metrics_post["request_rate"],
        "error_rate_percent": metrics_post["error_rate"],
        "p50_latency_ms": metrics_post["p50_latency_ms"],
        "p95_latency_ms": metrics_post["p95_latency_ms"],
        "p99_latency_ms": metrics_post["p99_latency_ms"],
        "baseline_error_rate_percent": metrics_pre["error_rate"],
        "baseline_p95_latency_ms": metrics_pre["p95_latency_ms"],
        "error_rate_delta_percent": round(metrics_post["error_rate"] - metrics_pre["error_rate"], 2),
        "latency_delta_ms": metrics_post["p95_latency_ms"] - metrics_pre["p95_latency_ms"],
        "observation": _health_observation(metrics_pre, metrics_post),
        "time_window_minutes": time_window_minutes,
        "checked_at": datetime.utcnow().isoformat(),
    }


def _health_observation(pre: Dict, post: Dict) -> str:
    delta_err = post["error_rate"] - pre["error_rate"]
    delta_lat = post["p95_latency_ms"] - pre["p95_latency_ms"]
    parts = []
    if delta_err > 10:
        parts.append(f"error rate increased significantly by {delta_err:.1f} percentage points")
    elif delta_err > 1:
        parts.append(f"error rate increased by {delta_err:.1f} percentage points")
    if delta_lat > 1000:
        parts.append(f"P95 latency degraded by {delta_lat} ms")
    if not parts:
        parts.append("no significant degradation detected")
    return "Service health check reveals: " + ", ".join(parts) + "."
