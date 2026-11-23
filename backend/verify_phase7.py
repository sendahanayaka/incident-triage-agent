"""Verification script for Phase 7 FastAPI backend implementation."""

import sys
from pathlib import Path

# Ensure repo root is in python path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fastapi.testclient import TestClient

from backend.app.approvals.manager import create_approval
from backend.app.core.config import settings
from backend.app.main import app


def run_verification() -> bool:
    print("=" * 60)
    print("PHASE 7 BACKEND API VERIFICATION")
    print("=" * 60)

    client = TestClient(app)
    passed = 0
    total = 0

    def check(name: str, condition: bool, details: str = "") -> None:
        nonlocal passed, total
        total += 1
        status = "PASSED" if condition else "FAILED"
        print(f"[{status}] {name}" + (f" - {details}" if details else ""))
        if condition:
            passed += 1

    # 1. Health check
    res = client.get("/api/health")
    check("GET /api/health", res.status_code == 200 and res.json().get("status") == "healthy", f"status={res.status_code}")

    # 2. Root discovery
    res = client.get("/")
    check("GET /", res.status_code == 200 and "docs" in res.json(), f"status={res.status_code}")

    # 3. OpenAPI docs
    res = client.get("/api/openapi.json")
    check("OpenAPI Schema", res.status_code == 200 and "paths" in res.json(), f"endpoints={len(res.json().get('paths', {}))}")

    # 4. Services
    res = client.get("/api/services")
    check("GET /api/services", res.status_code == 200 and len(res.json()) >= 3, f"count={len(res.json())}")

    # 5. Logs with filter
    res = client.get("/api/logs?service=payments-api&severity=ERROR&limit=5")
    check("GET /api/logs (filtered)", res.status_code == 200 and len(res.json()) > 0, f"returned={len(res.json())}")

    # 6. Deployments
    res = client.get("/api/deployments?service=payments-api")
    check("GET /api/deployments", res.status_code == 200 and len(res.json()) >= 2, f"returned={len(res.json())}")

    # 7. Start Investigation
    res = client.post("/api/investigations", json={"query": "Investigate payments-api failure"})
    inv_data = res.json()
    check("POST /api/investigations", res.status_code == 200 and inv_data.get("status") == "completed", f"id={inv_data.get('id')}")

    # 8. Retrieve Investigation
    inv_id = inv_data.get("id")
    res = client.get(f"/api/investigations/{inv_id}")
    check("GET /api/investigations/{id}", res.status_code == 200 and res.json().get("id") == inv_id, f"retrieved={inv_id}")

    # 9. Approvals workflow: create, pending, approve, duplicate check
    appr = create_approval(
        settings.resolved_database_path,
        action_type="create_incident_ticket",
        description="Verification approval ticket",
        parameters={
            "title": "Verification Outage",
            "severity": "HIGH",
            "summary": "Verified by verification script",
            "assignee": "qa-team",
        },
    )
    res = client.get("/api/approvals/pending")
    check("GET /api/approvals/pending", res.status_code == 200 and any(a["id"] == appr.id for a in res.json()), f"found pending={appr.id}")

    res = client.post(f"/api/approvals/{appr.id}/approve", json={"operator": "verifier", "note": "All good"})
    check("POST /api/approvals/{id}/approve", res.status_code == 200 and res.json().get("status") == "approved", f"status={res.json().get('status')}")

    # 10. Duplicate approval prevention
    res = client.post(f"/api/approvals/{appr.id}/approve")
    check("Duplicate approval prevention", res.status_code == 409, f"status={res.status_code} (expected 409)")

    # 11. Incidents retrieval (should include newly created ticket)
    res = client.get("/api/incidents")
    check("GET /api/incidents", res.status_code == 200 and any(i["title"] == "Verification Outage" for i in res.json()), f"total={len(res.json())}")

    # 12. Rejection workflow
    appr2 = create_approval(
        settings.resolved_database_path,
        action_type="restart_service",
        description="Verification restart action",
        parameters={"service": "auth-service"},
    )
    res = client.post(f"/api/approvals/{appr2.id}/reject", json={"operator": "verifier", "note": "Not needed"})
    check("POST /api/approvals/{id}/reject", res.status_code == 200 and res.json().get("status") == "rejected", f"status={res.json().get('status')}")

    # 13. Traces
    res = client.get("/api/traces")
    check("GET /api/traces", res.status_code == 200, f"traces_count={len(res.json())}")

    # 14. CORS headers
    res = client.options("/api/health", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"})
    check("CORS headers present", "access-control-allow-origin" in res.headers, f"origin_header={res.headers.get('access-control-allow-origin')}")

    # 15. Error Handling: Invalid input validation
    res = client.post("/api/investigations", json={"query": "x"})
    check("Input validation (422)", res.status_code == 422, f"status={res.status_code}")

    # 16. Error Handling: Not found (404)
    res = client.get("/api/investigations/inv-doesnotexist")
    check("Not found (404)", res.status_code == 404, f"status={res.status_code}")

    print("=" * 60)
    print(f"VERIFICATION SUMMARY: {passed}/{total} CHECKS PASSED")
    print("=" * 60)
    return passed == total


if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)
