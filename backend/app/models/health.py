"""Health check response model."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health status response."""

    status: str = Field(default="healthy", description="Status of the application")
    application: str = Field(default="IncidentTriageAgent", description="Application name")
    version: str = Field(default="1.0.0", description="Backend API version")
    environment: str = Field(default="development", description="Runtime environment")
