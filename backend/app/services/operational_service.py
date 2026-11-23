"""Operational data service for logs, deployments, and service health."""

import json
from pathlib import Path
from typing import Any

from backend.app.core.config import Settings, settings
from backend.app.models.deployment import DeploymentResponse
from backend.app.models.log import LogEntryResponse, LogSeverity
from backend.app.models.service import ServiceResponse


class OperationalService:
    """Service for accessing operational mock data (logs, deployments, runbooks)."""

    def __init__(self, app_settings: Settings = settings):
        self.settings = app_settings

    def _read_json_file(self, filename: str) -> list[dict[str, Any]]:
        file_path = self.settings.resolved_mock_data_dir / filename
        if not file_path.is_file():
            return []
        try:
            with file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    def get_logs(
        self,
        service: str | None = None,
        severity: str | None = None,
        limit: int = 50,
    ) -> list[LogEntryResponse]:
        """Retrieve operational logs with optional service, severity filters, and limit."""
        if severity:
            # Validate severity against allowed enum
            severity_upper = severity.upper()
            if severity_upper not in {s.value for s in LogSeverity}:
                raise ValueError(
                    f"Invalid severity '{severity}'. Allowed: {', '.join(s.value for s in LogSeverity)}"
                )
            severity = severity_upper

        raw_logs = self._read_json_file("logs.json")
        filtered: list[LogEntryResponse] = []

        for item in raw_logs:
            if service and item.get("service_name") != service:
                continue
            if severity and item.get("severity") != severity:
                continue
            filtered.append(
                LogEntryResponse(
                    id=item.get("id", ""),
                    timestamp=item.get("timestamp", ""),
                    service_name=item.get("service_name", ""),
                    severity=item.get("severity", "INFO"),
                    event=item.get("event", ""),
                    message=item.get("message", ""),
                )
            )
            if len(filtered) >= limit:
                break

        return filtered

    def get_deployments(self, service: str | None = None) -> list[DeploymentResponse]:
        """Retrieve deployment history with optional service filter."""
        raw_deployments = self._read_json_file("deployments.json")
        results: list[DeploymentResponse] = []

        for item in raw_deployments:
            if service and item.get("service_name") != service:
                continue
            results.append(
                DeploymentResponse(
                    deployment_id=item.get("deployment_id", ""),
                    service_name=item.get("service_name", ""),
                    version=item.get("version", ""),
                    commit_hash=item.get("commit_hash", ""),
                    timestamp=item.get("timestamp", ""),
                    status=item.get("status", "deployed"),
                    rollback_status=item.get("rollback_status", "not_requested"),
                    summary=item.get("summary", ""),
                )
            )

        return results

    def get_services(self) -> list[ServiceResponse]:
        """Retrieve simulated operational services aggregated from logs, deployments, and runbooks."""
        logs = self._read_json_file("logs.json")
        deployments = self._read_json_file("deployments.json")
        runbooks_dir = self.settings.resolved_mock_data_dir / "runbooks"

        # Unique service names
        service_names = sorted({
            item.get("service_name")
            for item in (logs + deployments)
            if item.get("service_name")
        })

        services: list[ServiceResponse] = []
        for name in service_names:
            runbook_path = runbooks_dir / f"{name}.md"
            runbook_exists = runbook_path.is_file()

            # Service deployments
            svc_deployments = [d for d in deployments if d.get("service_name") == name]
            latest_dep = svc_deployments[-1] if svc_deployments else None

            # Service error count
            svc_errors = [
                log for log in logs
                if log.get("service_name") == name and log.get("severity") in {"ERROR", "FATAL"}
            ]

            status = "degraded" if len(svc_errors) > 0 else "healthy"

            description = None
            if latest_dep:
                description = latest_dep.get("summary")

            services.append(
                ServiceResponse(
                    service_name=name,
                    status=status,
                    runbook_available=runbook_exists,
                    total_deployments=len(svc_deployments),
                    error_count=len(svc_errors),
                    latest_deployment_version=latest_dep.get("version") if latest_dep else None,
                    latest_deployment_time=latest_dep.get("timestamp") if latest_dep else None,
                    description=description,
                )
            )

        return services
