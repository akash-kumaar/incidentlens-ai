"""
Tool: inspect_metrics
Returns detailed resource metrics (CPU, memory, connections) for a service.
"""
from datetime import datetime
from typing import Dict, Any
from app.data.scenarios.scenario_data import ALL_SCENARIOS


def inspect_metrics(service_id: str, scenario_id: str, time_window_minutes: int = 60) -> Dict[str, Any]:
    scenario = ALL_SCENARIOS.get(scenario_id)
    if not scenario:
        return {"error": f"Scenario {scenario_id} not found"}

    pre = scenario["metrics"]["pre_incident"]
    post = scenario["metrics"]["post_incident"]

    return {
        "service_id": service_id,
        "time_window_minutes": time_window_minutes,
        "cpu": {
            "current_percent": post["cpu_percent"],
            "baseline_percent": pre["cpu_percent"],
            "delta": round(post["cpu_percent"] - pre["cpu_percent"], 1),
        },
        "memory": {
            "current_percent": post["memory_percent"],
            "baseline_percent": pre["memory_percent"],
            "delta": round(post["memory_percent"] - pre["memory_percent"], 1),
        },
        "connections": {
            "current_utilization_percent": post["connection_utilization"],
            "baseline_utilization_percent": pre["connection_utilization"],
            "delta": round(post["connection_utilization"] - pre["connection_utilization"], 1),
        },
        "request_rate": {
            "current_rps": post["request_rate"],
            "baseline_rps": pre["request_rate"],
        },
        "error_rate": {
            "current_percent": post["error_rate"],
            "baseline_percent": pre["error_rate"],
            "delta": round(post["error_rate"] - pre["error_rate"], 2),
        },
        "latency": {
            "p50_ms": post["p50_latency_ms"],
            "p95_ms": post["p95_latency_ms"],
            "p99_ms": post["p99_latency_ms"],
            "baseline_p50_ms": pre["p50_latency_ms"],
            "baseline_p95_ms": pre["p95_latency_ms"],
        },
        "observation": _metrics_observation(pre, post),
        "checked_at": datetime.utcnow().isoformat(),
    }


def _metrics_observation(pre: Dict, post: Dict) -> str:
    observations = []
    mem_delta = post["memory_percent"] - pre["memory_percent"]
    conn_delta = post["connection_utilization"] - pre["connection_utilization"]
    err_delta = post["error_rate"] - pre["error_rate"]

    if mem_delta > 30:
        observations.append(f"memory usage increased sharply by {mem_delta:.0f}% — approaching container limit")
    elif mem_delta > 10:
        observations.append(f"memory usage elevated by {mem_delta:.0f}%")

    if conn_delta > 50:
        observations.append(f"database connection utilization critically elevated by {conn_delta:.0f}%")
    elif conn_delta > 20:
        observations.append(f"connection pool utilization increased by {conn_delta:.0f}%")

    if err_delta > 15:
        observations.append(f"error rate dramatically elevated (+{err_delta:.1f}%)")

    if not observations:
        observations.append("no significant resource anomalies detected")

    return "Metrics analysis: " + "; ".join(observations) + "."
