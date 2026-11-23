"""Service status and metrics models."""

from pydantic import BaseModel, Field


class ServiceResponse(BaseModel):
    """Operational service status and details."""

    service_name: str = Field(..., description="Service identifier, e.g. payments-api")
    status: str = Field(default="healthy", description="Operational status: healthy, degraded, critical")
    runbook_available: bool = Field(default=False, description="Whether an operational runbook exists")
    total_deployments: int = Field(default=0, description="Number of recorded deployments")
    error_count: int = Field(default=0, description="Recent error log count")
    latest_deployment_version: str | None = Field(default=None, description="Latest deployed version")
    latest_deployment_time: str | None = Field(default=None, description="Timestamp of latest deployment")
    description: str | None = Field(default=None, description="Service summary or description")


class ServicesListResponse(BaseModel):
    """List of operational services."""

    services: list[ServiceResponse] = Field(default_factory=list)
    total: int = Field(default=0)
