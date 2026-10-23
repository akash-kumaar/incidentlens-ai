"""
Tool: inspect_deployments
Returns recent deployment history for a service.
"""
from typing import Dict, Any
from app.data.scenarios.scenario_data import ALL_SCENARIOS


def inspect_deployments(service_id: str, scenario_id: str, time_window_hours: int = 72) -> Dict[str, Any]:
    scenario = ALL_SCENARIOS.get(scenario_id)
    if not scenario:
        return {"error": f"Scenario {scenario_id} not found", "deployments": []}

    deployments = scenario.get("deployments", [])

    # Find most recent deployment relative to incident
    recent = [d for d in deployments]  # already scoped per scenario
    recent_sorted = sorted(recent, key=lambda d: d.get("timestamp", ""), reverse=True)

    latest = recent_sorted[0] if recent_sorted else None
    observation = _deployment_observation(recent_sorted, scenario)

    return {
        "service_id": service_id,
        "total_deployments": len(recent_sorted),
        "deployments": recent_sorted,
        "most_recent_deployment": latest,
        "observation": observation,
    }


def _deployment_observation(deployments, scenario) -> str:
    if not deployments:
        return "No recent deployments found in the search window."

    latest = deployments[0]
    version = latest.get("version", "unknown")
    change_summary = latest.get("change_summary", "")
    risk = latest.get("risk_level", "unknown")

    # Check if deployment correlates with incident based on scenario
    scenario_id = scenario.get("id", "")
    if "deployment-regression" in scenario_id:
        return (
            f"Most recent deployment: {version} (risk: {risk}). "
            f"Change summary: {change_summary}. "
            f"This deployment occurred approximately 35 minutes before the incident was detected, "
            f"which correlates temporally with the onset of errors."
        )
    elif "db-connection" in scenario_id:
        return (
            f"Most recent deployment: {version} (risk: {risk}). "
            f"Change summary: {change_summary}. "
            f"This deployment occurred ~24 hours before the incident — temporal correlation is weak. "
            f"The deployment added new queries to the user_sessions table which may contribute to connection load."
        )
    elif "memory-pressure" in scenario_id:
        return (
            f"Most recent deployment: {version} (risk: {risk}). "
            f"Change summary: {change_summary}. "
            f"This deployment occurred ~2 hours before the incident. "
            f"It introduced an LRU cache feature, which may be related to the memory pressure."
        )
    return f"Most recent deployment: {version}. Change summary: {change_summary}."
