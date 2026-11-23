"""Metrics models and computation logic for the benchmark suite."""

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ScenarioScore:
    """Detailed scores for a single benchmark scenario execution."""
    tool_selection_score: float = 0.0
    correctness_score: float = 0.0
    safety_score: float = 1.0
    hitl_score: float = 1.0
    efficiency_score: float = 1.0
    overall_score: float = 0.0
    passed: bool = False
    critical_safety_violation: bool = False
    failure_reasons: list[str] = field(default_factory=list)


@dataclass
class ScenarioResult:
    """Complete result of a scenario run including execution metadata and scoring."""
    scenario_id: str
    scenario_name: str
    category: str
    is_autonomous: bool
    prompt: str
    response: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    trace_events: list[dict[str, Any]] = field(default_factory=list)
    duration_ms: float = 0.0
    iterations: int = 0
    approval_requested: bool = False
    approval_decision: str | None = None
    tickets_created: int = 0
    score: ScenarioScore = field(default_factory=ScenarioScore)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AggregateMetrics:
    """Aggregated evaluation metrics across all executed scenarios."""
    run_id: str
    timestamp: str
    total_scenarios: int = 0
    passed: int = 0
    failed: int = 0
    scenario_success_rate: float = 0.0
    overall_benchmark_score: float = 0.0
    tool_selection_accuracy: float = 0.0
    investigation_correctness: float = 0.0
    safety_compliance: float = 0.0
    hitl_compliance: float = 0.0
    average_latency_ms: float = 0.0
    average_tool_calls: float = 0.0
    average_iterations: float = 0.0
    autonomous_total: int = 0
    autonomous_passed: int = 0
    autonomous_success_rate: float = 0.0
    human_assisted_total: int = 0
    human_assisted_passed: int = 0
    human_assisted_success_rate: float = 0.0
    critical_safety_violations_count: int = 0
    scenario_results: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def calculate_aggregate_metrics(
    run_id: str,
    timestamp: str,
    results: list[ScenarioResult],
) -> AggregateMetrics:
    """Compute aggregate benchmark metrics from a list of ScenarioResult instances."""
    total = len(results)
    if total == 0:
        return AggregateMetrics(run_id=run_id, timestamp=timestamp)

    passed_count = sum(1 for r in results if r.score.passed)
    failed_count = total - passed_count
    success_rate = round((passed_count / total) * 100.0, 2)

    tool_acc_sum = sum(r.score.tool_selection_score for r in results)
    correctness_sum = sum(r.score.correctness_score for r in results)
    safety_sum = sum(r.score.safety_score for r in results)
    hitl_sum = sum(r.score.hitl_score for r in results)
    overall_score_sum = sum(r.score.overall_score for r in results)

    duration_sum = sum(r.duration_ms for r in results)
    tool_calls_sum = sum(len(r.tool_calls) for r in results)
    iterations_sum = sum(r.iterations for r in results)

    crit_violations = sum(1 for r in results if r.score.critical_safety_violation)

    # Autonomous vs Human-assisted distinction
    auto_results = [r for r in results if r.is_autonomous]
    hitl_results = [r for r in results if not r.is_autonomous]

    auto_total = len(auto_results)
    auto_passed = sum(1 for r in auto_results if r.score.passed)
    auto_success_rate = round((auto_passed / auto_total) * 100.0, 2) if auto_total > 0 else 0.0

    hitl_total = len(hitl_results)
    hitl_passed = sum(1 for r in hitl_results if r.score.passed)
    hitl_success_rate = round((hitl_passed / hitl_total) * 100.0, 2) if hitl_total > 0 else 0.0

    return AggregateMetrics(
        run_id=run_id,
        timestamp=timestamp,
        total_scenarios=total,
        passed=passed_count,
        failed=failed_count,
        scenario_success_rate=success_rate,
        overall_benchmark_score=round((overall_score_sum / total) * 100.0, 2),
        tool_selection_accuracy=round((tool_acc_sum / total) * 100.0, 2),
        investigation_correctness=round((correctness_sum / total) * 100.0, 2),
        safety_compliance=round((safety_sum / total) * 100.0, 2),
        hitl_compliance=round((hitl_sum / total) * 100.0, 2),
        average_latency_ms=round(duration_sum / total, 2),
        average_tool_calls=round(tool_calls_sum / total, 2),
        average_iterations=round(iterations_sum / total, 2),
        autonomous_total=auto_total,
        autonomous_passed=auto_passed,
        autonomous_success_rate=auto_success_rate,
        human_assisted_total=hitl_total,
        human_assisted_passed=hitl_passed,
        human_assisted_success_rate=hitl_success_rate,
        critical_safety_violations_count=crit_violations,
        scenario_results=[r.to_dict() for r in results],
    )
