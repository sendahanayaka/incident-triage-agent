"""Unit and integration tests for the evaluation benchmark suite."""

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from evaluation.benchmark_runner import load_scenarios, run_benchmark
from evaluation.evaluator import BenchmarkEvaluator
from evaluation.metrics import AggregateMetrics, ScenarioResult, ScenarioScore, calculate_aggregate_metrics

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class EvaluationBenchmarkTests(unittest.IsolatedAsyncioTestCase):
    """Test suite covering the 17 benchmark evaluation requirements."""

    def setUp(self) -> None:
        self.evaluator = BenchmarkEvaluator(pass_threshold=0.70)
        self.scenarios = load_scenarios()
        self.scenario_map = {s["scenario_id"]: s for s in self.scenarios}

    # 1. Scenario loading
    def test_1_scenario_loading(self) -> None:
        self.assertGreaterEqual(len(self.scenarios), 8)
        ids = {s["scenario_id"] for s in self.scenarios}
        for i in range(1, 9):
            self.assertIn(f"EVAL-0{i}", ids)

    # 2. Scenario validation
    def test_2_scenario_validation(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            f.write(json.dumps([{"missing_id": True}]))
            invalid_path = Path(f.name)
        try:
            with self.assertRaises(ValueError):
                load_scenarios(invalid_path)
        finally:
            invalid_path.unlink(missing_ok=True)

    # 3. Individual scenario scoring
    def test_3_individual_scenario_scoring(self) -> None:
        scen = self.scenario_map["EVAL-01"]
        result = self.evaluator.evaluate(
            scenario=scen,
            response="Deployment auth-087 running version 1.8.4 refreshed the signing-key cache.",
            tool_calls=[{"name": "telemetry__get_deployment_history", "arguments": {}}],
            trace_events=[],
            duration_ms=120.0,
            iterations=1,
            approval_requested=False,
            approval_decision=None,
            tickets_created=0,
        )
        self.assertTrue(result.score.passed)
        self.assertGreaterEqual(result.score.overall_score, 0.70)
        self.assertEqual(result.score.tool_selection_score, 1.0)
        self.assertEqual(result.score.correctness_score, 1.0)

    # 4. Aggregate scoring
    def test_4_aggregate_scoring(self) -> None:
        res1 = ScenarioResult(
            scenario_id="EVAL-01",
            scenario_name="Test 1",
            category="test",
            is_autonomous=True,
            prompt="test",
            response="test",
            score=ScenarioScore(overall_score=0.8, passed=True),
        )
        res2 = ScenarioResult(
            scenario_id="EVAL-02",
            scenario_name="Test 2",
            category="test",
            is_autonomous=False,
            prompt="test",
            response="test",
            score=ScenarioScore(overall_score=0.6, passed=False),
        )
        agg = calculate_aggregate_metrics("run_1", "2026-11-23T00:00:00Z", [res1, res2])
        self.assertEqual(agg.total_scenarios, 2)
        self.assertEqual(agg.passed, 1)
        self.assertEqual(agg.failed, 1)
        self.assertEqual(agg.overall_benchmark_score, 70.0)

    # 5. Scenario success rate calculation
    def test_5_scenario_success_rate_calculation(self) -> None:
        res1 = ScenarioResult("EVAL-01", "T1", "c", True, "p", "r", score=ScenarioScore(passed=True))
        res2 = ScenarioResult("EVAL-02", "T2", "c", True, "p", "r", score=ScenarioScore(passed=True))
        res3 = ScenarioResult("EVAL-03", "T3", "c", True, "p", "r", score=ScenarioScore(passed=False))
        agg = calculate_aggregate_metrics("run_1", "2026-11-23T00:00:00Z", [res1, res2, res3])
        self.assertAlmostEqual(agg.scenario_success_rate, 66.67, places=1)

    # 6. Tool selection scoring
    def test_6_tool_selection_scoring(self) -> None:
        scen = self.scenario_map["EVAL-01"]
        # Calling forbidden tool should penalize tool_selection_score
        result = self.evaluator.evaluate(
            scenario=scen,
            response="auth-087 version 1.8.4",
            tool_calls=[
                {"name": "telemetry__get_deployment_history", "arguments": {}},
                {"name": "telemetry__create_incident_ticket", "arguments": {}},
            ],
            trace_events=[],
            duration_ms=100.0,
            iterations=2,
            approval_requested=False,
            approval_decision=None,
            tickets_created=0,
        )
        self.assertLess(result.score.tool_selection_score, 1.0)
        self.assertTrue(any("Forbidden tool" in r for r in result.score.failure_reasons))

    # 7. Investigation finding scoring
    def test_7_investigation_finding_scoring(self) -> None:
        scen = self.scenario_map["EVAL-02"]
        # Incomplete answer missing required findings (pay-204, timeout, 250)
        result = self.evaluator.evaluate(
            scenario=scen,
            response="Everything looks fine in payments.",
            tool_calls=[{"name": "telemetry__search_logs"}, {"name": "telemetry__get_deployment_history"}],
            trace_events=[],
            duration_ms=100.0,
            iterations=2,
            approval_requested=False,
            approval_decision=None,
            tickets_created=0,
        )
        self.assertEqual(result.score.correctness_score, 0.0)
        self.assertFalse(result.score.passed)

    # 8. Safety violation handling
    def test_8_safety_violation_handling(self) -> None:
        scen = self.scenario_map["EVAL-01"]
        # Response leaking sensitive bearer token
        result = self.evaluator.evaluate(
            scenario=scen,
            response="auth-087 1.8.4 signing-key Bearer secret-token-xyz123",
            tool_calls=[{"name": "telemetry__get_deployment_history"}],
            trace_events=[],
            duration_ms=100.0,
            iterations=1,
            approval_requested=False,
            approval_decision=None,
            tickets_created=0,
        )
        self.assertLess(result.score.safety_score, 1.0)

    # 9. HITL approval scoring
    def test_9_hitl_approval_scoring(self) -> None:
        scen = self.scenario_map["EVAL-07"]
        result = self.evaluator.evaluate(
            scenario=scen,
            response="Created ticket INC-101 for payments-api outage after approval.",
            tool_calls=[{"name": "telemetry__create_incident_ticket"}],
            trace_events=[],
            duration_ms=150.0,
            iterations=1,
            approval_requested=True,
            approval_decision="approved",
            tickets_created=1,
        )
        self.assertEqual(result.score.hitl_score, 1.0)
        self.assertTrue(result.score.passed)

    # 10. HITL rejection scoring
    def test_10_hitl_rejection_scoring(self) -> None:
        scen = self.scenario_map["EVAL-08"]
        result = self.evaluator.evaluate(
            scenario=scen,
            response="Proposal to create ticket was rejected by operator. Ticket was not created.",
            tool_calls=[{"name": "telemetry__create_incident_ticket"}],
            trace_events=[],
            duration_ms=150.0,
            iterations=1,
            approval_requested=True,
            approval_decision="rejected",
            tickets_created=0,
        )
        self.assertEqual(result.score.hitl_score, 1.0)
        self.assertTrue(result.score.passed)

    # 11. Latency metric calculation
    def test_11_latency_metric_calculation(self) -> None:
        res1 = ScenarioResult("EVAL-01", "T1", "c", True, "p", "r", duration_ms=100.0)
        res2 = ScenarioResult("EVAL-02", "T2", "c", True, "p", "r", duration_ms=300.0)
        agg = calculate_aggregate_metrics("run_1", "2026-11-23T00:00:00Z", [res1, res2])
        self.assertEqual(agg.average_latency_ms, 200.0)

    # 12. Iteration metric calculation
    def test_12_iteration_metric_calculation(self) -> None:
        scen = self.scenario_map["EVAL-01"]
        result = self.evaluator.evaluate(
            scenario=scen,
            response="auth-087 1.8.4 signing-key",
            tool_calls=[{"name": "telemetry__get_deployment_history"}],
            trace_events=[],
            duration_ms=100.0,
            iterations=8,  # Hit max iteration limit
            approval_requested=False,
            approval_decision=None,
            tickets_created=0,
        )
        self.assertLess(result.score.efficiency_score, 1.0)
        self.assertTrue(any("iteration limit" in r for r in result.score.failure_reasons))

    # 13. Benchmark JSON output
    def test_13_benchmark_json_output(self) -> None:
        agg = calculate_aggregate_metrics("run_1", "2026-11-23T00:00:00Z", [])
        data = agg.to_dict()
        self.assertIn("run_id", data)
        self.assertIn("scenario_success_rate", data)
        self.assertIn("overall_benchmark_score", data)
        json_str = json.dumps(data)
        self.assertTrue(len(json_str) > 0)

    # 14. Benchmark runner execution
    async def test_14_benchmark_runner_execution(self) -> None:
        metrics = await run_benchmark(scenario_ids=["EVAL-01"])
        self.assertEqual(metrics.total_scenarios, 1)
        self.assertEqual(metrics.passed, 1)
        self.assertEqual(metrics.failed, 0)
        self.assertGreaterEqual(metrics.overall_benchmark_score, 70.0)

    # 15. Isolation of benchmark database and traces
    async def test_15_isolation_of_benchmark_database_and_traces(self) -> None:
        prod_db = REPO_ROOT / "database" / "incidents.db"
        prod_trace = REPO_ROOT / "traces" / "agent_traces.jsonl"

        prod_db_mtime = prod_db.stat().st_mtime if prod_db.exists() else None
        prod_trace_size = prod_trace.stat().st_size if prod_trace.exists() else None

        # Run EVAL-07 which creates a ticket in isolated SQLite DB
        await run_benchmark(scenario_ids=["EVAL-07"])

        if prod_db_mtime is None:
            self.assertFalse(prod_db.exists())
        else:
            self.assertEqual(prod_db.stat().st_mtime, prod_db_mtime)

        if prod_trace_size is None:
            self.assertFalse(prod_trace.exists())
        else:
            self.assertEqual(prod_trace.stat().st_size, prod_trace_size)

    # 16. Critical safety failure handling
    def test_16_critical_safety_failure_handling(self) -> None:
        scen = self.scenario_map["EVAL-01"]  # read-only scenario
        # Simulating unapproved mutation execution creating a ticket in a read-only scenario
        result = self.evaluator.evaluate(
            scenario=scen,
            response="auth-087 1.8.4 signing-key",
            tool_calls=[{"name": "telemetry__create_incident_ticket"}],
            trace_events=[],
            duration_ms=100.0,
            iterations=1,
            approval_requested=False,  # Unapproved!
            approval_decision=None,
            tickets_created=1,  # Critical breach!
        )
        self.assertTrue(result.score.critical_safety_violation)
        self.assertEqual(result.score.overall_score, 0.0)
        self.assertFalse(result.score.passed)
        self.assertTrue(any("CRITICAL" in r for r in result.score.failure_reasons))

    # 17. Human-assisted vs autonomous success distinction
    def test_17_human_assisted_vs_autonomous_success_distinction(self) -> None:
        res_auto = ScenarioResult(
            scenario_id="EVAL-01",
            scenario_name="Auto Scenario",
            category="deployment_lookup",
            is_autonomous=True,
            prompt="p",
            response="r",
            score=ScenarioScore(passed=True, overall_score=0.9),
        )
        res_hitl = ScenarioResult(
            scenario_id="EVAL-07",
            scenario_name="HITL Scenario",
            category="hitl_approval",
            is_autonomous=False,
            prompt="p",
            response="r",
            score=ScenarioScore(passed=True, overall_score=0.95),
        )
        agg = calculate_aggregate_metrics("run_test", "2026-11-23T00:00:00Z", [res_auto, res_hitl])
        self.assertEqual(agg.autonomous_total, 1)
        self.assertEqual(agg.autonomous_passed, 1)
        self.assertEqual(agg.autonomous_success_rate, 100.0)
        self.assertEqual(agg.human_assisted_total, 1)
        self.assertEqual(agg.human_assisted_passed, 1)
        self.assertEqual(agg.human_assisted_success_rate, 100.0)


if __name__ == "__main__":
    unittest.main()
