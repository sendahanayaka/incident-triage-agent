"""Health check and LLM provider status response models."""

from pydantic import BaseModel, Field


class LLMConfigStatus(BaseModel):
    """Safe, non-secret LLM configuration status."""

    provider: str = Field(default="offline", description="Active LLM provider: openrouter or offline")
    mode: str = Field(default="offline", description="Operating mode: live or offline")
    model: str = Field(default="", description="Configured model identifier")
    has_api_key: bool = Field(default=False, description="Whether an API key is configured (boolean only)")
    base_url: str = Field(default="https://openrouter.ai/api/v1", description="Configured API base URL")
    is_ready: bool = Field(default=True, description="Whether configuration is valid and ready to execute")


class HealthResponse(BaseModel):
    """Health status response with non-secret provider information."""

    status: str = Field(default="healthy", description="Status of the application")
    application: str = Field(default="IncidentTriageAgent", description="Application name")
    version: str = Field(default="1.0.0", description="Backend API version")
    environment: str = Field(default="development", description="Runtime environment")
    llm: LLMConfigStatus = Field(default_factory=LLMConfigStatus, description="LLM provider and operating mode status")
