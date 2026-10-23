"""
Tool: inspect_logs
Retrieves and filters log entries for a service within a time window.
"""
from typing import List, Dict, Any, Optional
from app.data.scenarios.scenario_data import ALL_SCENARIOS


def inspect_logs(
    service_id: str,
    scenario_id: str,
    time_window_minutes: int = 60,
    severity: Optional[str] = None,
    search_term: Optional[str] = None,
) -> Dict[str, Any]:
    scenario = ALL_SCENARIOS.get(scenario_id)
    if not scenario:
        return {"error": f"Scenario {scenario_id} not found", "logs": []}

    logs = scenario.get("logs", [])

    # Filter by service
    logs = [l for l in logs if l.get("service") == service_id]

    # Filter by severity
    if severity:
        logs = [l for l in logs if l.get("level", "").upper() == severity.upper()]

    # Filter by search term
    if search_term:
        term = search_term.lower()
        logs = [l for l in logs if term in l.get("message", "").lower()]

    # Sort by timestamp ascending
    logs = sorted(logs, key=lambda x: x.get("timestamp", ""))

    error_count = sum(1 for l in logs if l.get("level") == "ERROR")
    warn_count = sum(1 for l in logs if l.get("level") == "WARN")
    info_count = sum(1 for l in logs if l.get("level") == "INFO")

    return {
        "service_id": service_id,
        "scenario_id": scenario_id,
        "total_entries": len(logs),
        "error_count": error_count,
        "warn_count": warn_count,
        "info_count": info_count,
        "log_entries": logs,
        "observation": _log_observation(logs, error_count),
    }


def _log_observation(logs: List[Dict], error_count: int) -> str:
    if error_count == 0:
        return "No error-level log entries found in the specified window."
    # Find most repeated error pattern
    messages = [l.get("message", "") for l in logs if l.get("level") == "ERROR"]
    if messages:
        # Find common keyword
        first_msg = messages[0]
        if "NullPointerException" in first_msg or "RequestProcessingError" in first_msg:
            return f"Found {error_count} ERROR entries. Dominant pattern: RequestProcessingError / NullPointerException indicating a code-level regression."
        if "ConnectionTimeoutError" in first_msg or "pool exhausted" in first_msg:
            return f"Found {error_count} ERROR entries. Dominant pattern: ConnectionTimeoutError indicating database connection pool exhaustion."
        if "OOM Killer" in first_msg or "FATAL" in first_msg:
            return f"Found {error_count} ERROR entries. Dominant pattern: OOM kills, suggesting container memory limit is being exceeded repeatedly."
    return f"Found {error_count} ERROR entries in the log window."
