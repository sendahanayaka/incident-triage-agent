"""Deployment models."""

from pydantic import BaseModel, Field


class DeploymentResponse(BaseModel):
    """Deployment record."""

    deployment_id: str = Field(..., description="Deployment identifier, e.g. pay-204")
    service_name: str = Field(..., description="Target service name")
    version: str = Field(..., description="Deployed semantic version")
    commit_hash: str = Field(..., description="Git commit hash")
    timestamp: str = Field(..., description="UTC ISO timestamp of deployment")
    status: str = Field(..., description="Deployment status, e.g. deployed")
    rollback_status: str = Field(..., description="Rollback status: not_requested, rolled_back, etc.")
    summary: str = Field(..., description="Release changelog summary")


class DeploymentsListResponse(BaseModel):
    """List of deployment records."""

    deployments: list[DeploymentResponse] = Field(default_factory=list)
    total: int = Field(default=0)
