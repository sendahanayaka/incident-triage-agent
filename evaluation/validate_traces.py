"""Validate the integrity, structure, and safety of sample execution traces."""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
TRACES_DIR = REPO_ROOT / "traces"

REQUIRED_FIELDS = {"timestamp", "run_id", "tool", "arguments", "duration_ms", "status"}
SENSITIVE_PATTERNS = ["secret-token-", "bearer ", "password123", "api_key_secret"]

TRACE_FILES = [
    {
        "path": TRACES_DIR / "sample_root_cause_investigation.jsonl",
        "name": "Trace A: Root Cause Investigation",
        "expected_tools": ["telemetry__search_logs", "telemetry__get_deployment_history"],
        "expect_approval": None,
    },
    {
        "path": TRACES_DIR / "sample_hitl_approved.jsonl",
        "name": "Trace B: Human-Approved Ticket Creation",
        "expected_tools": ["telemetry__create_incident_ticket"],
        "expect_approval": "approved",
        "expect_status": "ok",
    },
    {
        "path": TRACES_DIR / "sample_hitl_rejected.jsonl",
        "name": "Trace C: Human-Rejected Ticket Creation",
        "expected_tools": ["telemetry__create_incident_ticket"],
        "expect_approval": "rejected",
        "expect_status": "rejected",
    },
    {
        "path": TRACES_DIR / "sample_prompt_injection_defense.jsonl",
        "name": "Trace D: Prompt Injection Defense",
        "expected_tools": ["telemetry__search_logs"],
        "expect_approval": None,
    },
]


def validate_trace_file(spec: dict[str, Any]) -> tuple[bool, list[str]]:
    path: Path = spec["path"]
    name: str = spec["name"]
    errors: list[str] = []

    if not path.is_file():
        return False, [f"File does not exist: {path}"]
    if path.stat().st_size == 0:
        return False, [f"File is empty: {path}"]

    events: list[dict[str, Any]] = []
    line_number = 0
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line_number += 1
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as e:
                errors.append(f"Line {line_number}: Invalid JSON: {e}")
                continue
            events.append(event)

    if not events:
        return False, [f"{name}: No JSON events found."]

    # 1. Field validation
    for idx, ev in enumerate(events, 1):
        missing = REQUIRED_FIELDS - set(ev.keys())
        if missing:
            errors.append(f"Event {idx}: Missing required fields: {missing}")

    # 2. Chronological ordering
    timestamps: list[datetime] = []
    for idx, ev in enumerate(events, 1):
        ts_str = ev.get("timestamp")
        if ts_str:
            try:
                timestamps.append(datetime.fromisoformat(ts_str.replace("Z", "+00:00")))
            except ValueError:
                errors.append(f"Event {idx}: Invalid ISO-8601 timestamp '{ts_str}'")

    for i in range(1, len(timestamps)):
        if timestamps[i] < timestamps[i - 1]:
            errors.append(f"Events out of chronological order at index {i}")

    # 3. Correlation / Run ID consistency
    run_ids = {ev.get("run_id") for ev in events if ev.get("run_id")}
    if len(run_ids) != 1:
        errors.append(f"Inconsistent run_ids in trace: {run_ids}")

    # 4. Tool verification
    tools_in_trace = [ev.get("tool") for ev in events]
    for exp_tool in spec.get("expected_tools", []):
        if exp_tool not in tools_in_trace:
            errors.append(f"Expected tool '{exp_tool}' not found in trace. Found: {tools_in_trace}")

    # 5. Approval / Rejection verification
    expected_decision = spec.get("expect_approval")
    if expected_decision:
        found_approval = False
        for ev in events:
            if ev.get("approval_required") is True:
                actual_dec = ev.get("approval_decision")
                if actual_dec == expected_decision:
                    found_approval = True
                    expected_status = spec.get("expect_status")
                    if expected_status and ev.get("status") != expected_status:
                        errors.append(f"Expected event status '{expected_status}', got '{ev.get('status')}'")
        if not found_approval:
            errors.append(f"Expected approval event with decision '{expected_decision}' was not found.")

    # 6. Secret / Credential exposure check
    for idx, ev in enumerate(events, 1):
        ev_str = json.dumps(ev).lower()
        for pattern in SENSITIVE_PATTERNS:
            if pattern in ev_str:
                errors.append(f"Event {idx}: Potential sensitive secret leak detected: '{pattern}'")

    return len(errors) == 0, errors


def main() -> int:
    print("=" * 70)
    print(" TRACE VALIDATION SUITE")
    print("=" * 70 + "\n")
    all_ok = True

    for spec in TRACE_FILES:
        ok, errors = validate_trace_file(spec)
        status_label = "[PASS]" if ok else "[FAIL]"
        print(f"{status_label} {spec['name']} ({spec['path'].name})")
        if not ok:
            all_ok = False
            for err in errors:
                print(f"   -> Error: {err}")
        else:
            print(f"   -> Validated JSONL structure, chronology, run_id, and secret hygiene.")

    print("\n" + "=" * 70)
    if all_ok:
        print(" All sample execution traces successfully validated with 0 errors.")
        print("=" * 70)
        return 0
    else:
        print(" Trace validation failed.")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
