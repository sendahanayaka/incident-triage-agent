"""Core configuration and settings for the Incident Triage & Release Readiness Agent."""

import os
from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Base paths
APP_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = APP_DIR.parent
REPO_ROOT = BACKEND_DIR.parent

# Load environment variables from repo root .env if present
load_dotenv(REPO_ROOT / ".env")


class Settings(BaseModel):
    """Application settings loaded from environment variables."""

    app_name: str = Field(default_factory=lambda: os.getenv("APP_NAME", "IncidentTriageAgent"))
    app_env: str = Field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    api_prefix: str = "/api"

    # Database
    database_path: str = Field(default_factory=lambda: os.getenv("DATABASE_PATH", "database/incidents.db"))

    # MCP and Filesystem Paths
    rust_mcp_server_path: str = Field(
        default_factory=lambda: os.getenv(
            "RUST_MCP_SERVER_PATH", "mcp-server/target/debug/ops-telemetry-mcp.exe"
        )
    )
    filesystem_workspace: str = Field(
        default_factory=lambda: os.getenv("FILESYSTEM_WORKSPACE", "mock_data/workspace")
    )
    mock_data_dir: str = Field(default_factory=lambda: os.getenv("MOCK_DATA_DIR", "mock_data"))
    trace_file_path: str = Field(
        default_factory=lambda: os.getenv("TRACE_FILE_PATH", "traces/agent_traces.jsonl")
    )

    # LLM and Agent Configuration (OpenRouter & Strict Offline Mode)
    llm_provider: str = Field(
        default_factory=lambda: (os.getenv("LLM_PROVIDER") or "offline").strip().lower()
    )
    llm_mode: str = Field(
        default_factory=lambda: (os.getenv("LLM_MODE") or "offline").strip().lower()
    )
    llm_api_key: str = Field(
        default_factory=lambda: (os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    )
    llm_model: str = Field(default_factory=lambda: (os.getenv("LLM_MODEL") or "").strip())
    llm_base_url: str = Field(
        default_factory=lambda: (os.getenv("LLM_BASE_URL") or "https://openrouter.ai/api/v1").strip()
    )
    max_agent_iterations: int = Field(
        default_factory=lambda: int(os.getenv("MAX_AGENT_ITERATIONS", "8"))
    )
    agent_tool_timeout_seconds: float = Field(
        default_factory=lambda: float(os.getenv("AGENT_TOOL_TIMEOUT_SECONDS", "10"))
    )

    @property
    def is_offline_mode(self) -> bool:
        return self.llm_mode == "offline" or self.llm_provider == "offline"

    @property
    def has_llm_api_key(self) -> bool:
        clean = self.llm_api_key.strip()
        return bool(clean and clean.lower() not in {"your-api-key", "none", "mock-key", ""})

    # CORS
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    @property
    def resolved_database_path(self) -> Path:
        path = Path(self.database_path)
        return path if path.is_absolute() else (REPO_ROOT / path)

    @property
    def resolved_mock_data_dir(self) -> Path:
        path = Path(self.mock_data_dir)
        return path if path.is_absolute() else (REPO_ROOT / path)

    @property
    def resolved_trace_file_path(self) -> Path:
        path = Path(self.trace_file_path)
        return path if path.is_absolute() else (REPO_ROOT / path)

    @property
    def resolved_rust_mcp_path(self) -> Path:
        path = Path(self.rust_mcp_server_path)
        return path if path.is_absolute() else (REPO_ROOT / path)

    @property
    def resolved_workspace_path(self) -> Path:
        path = Path(self.filesystem_workspace)
        return path if path.is_absolute() else (REPO_ROOT / path)


settings = Settings()
