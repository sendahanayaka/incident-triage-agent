"""Safety guardrails and policy enforcement for agent actions."""

from enum import Enum


class ActionRiskLevel(str, Enum):
    """Risk tier classifications for agent actions."""

    READ_ONLY = "READ_ONLY"
    LOW_RISK_MUTATION = "LOW_RISK_MUTATION"
    HIGH_RISK_MUTATION = "HIGH_RISK_MUTATION"


# Actions statically classified as read-only and safe to execute autonomously
READ_ONLY_ACTIONS = frozenset({
    "search_logs",
    "telemetry__search_logs",
    "get_deployment_history",
    "telemetry__get_deployment_history",
    "read_resource",
    "telemetry__read_resource",
    "read_text_file",
    "filesystem__read_text_file",
    "list_directory",
    "filesystem__list_directory",
    "list_allowed_directories",
    "filesystem__list_allowed_directories",
})

# Actions that mutate state and require explicit Human-in-the-Loop approval
MUTATION_ACTIONS = frozenset({
    "create_incident_ticket",
    "telemetry__create_incident_ticket",
    "rollback_deployment",
    "restart_service",
    "scale_service",
})


def is_safe_action(action_name: str) -> bool:
    """Check whether an action is read-only and safe for autonomous execution."""
    return action_name in READ_ONLY_ACTIONS


def requires_approval(action_name: str) -> bool:
    """Check whether an action requires explicit human approval before execution."""
    return not is_safe_action(action_name)


def classify_risk(action_name: str) -> ActionRiskLevel:
    """Classify the risk level of a tool or action."""
    if is_safe_action(action_name):
        return ActionRiskLevel.READ_ONLY
    if action_name in {"create_incident_ticket", "telemetry__create_incident_ticket"}:
        return ActionRiskLevel.LOW_RISK_MUTATION
    return ActionRiskLevel.HIGH_RISK_MUTATION


def validate_action_execution(action_name: str, is_approved: bool = False) -> tuple[bool, str]:
    """Validate whether an action can proceed based on safety policies."""
    if is_safe_action(action_name):
        return True, "Action is read-only and pre-approved."
    if is_approved:
        return True, "Action was explicitly approved by an operator."
    return False, f"Action '{action_name}' modifies state and requires human approval."
