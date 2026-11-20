use std::{
    env,
    path::{Path, PathBuf},
};

use chrono::{DateTime, Utc};
use rmcp::{
    ErrorData, RoleServer, ServerHandler,
    handler::server::router::tool::ToolRouter,
    model::{
        Implementation, ListResourceTemplatesResult, ListResourcesResult, PaginatedRequestParams,
        ReadResourceRequestParams, ReadResourceResponse, ReadResourceResult, ServerCapabilities,
        ServerConfig,
    },
    service::RequestContext,
    tool_handler,
};

use crate::{data::TelemetryData, errors::ServerError, resources};

const DEMO_REFERENCE_TIME: &str = "2026-11-20T04:30:00Z";

pub(crate) struct TelemetryServer {
    pub(crate) data: TelemetryData,
    pub(crate) reference_time: DateTime<Utc>,
    pub(crate) ticket_path: PathBuf,
    tool_router: ToolRouter<Self>,
}

impl TelemetryServer {
    pub(crate) fn from_environment() -> Result<Self, ServerError> {
        let root = if Path::new("mock_data").is_dir() || !Path::new("../mock_data").is_dir() {
            Path::new(".")
        } else {
            Path::new("..")
        };
        let data_dir = env::var_os("OPS_TELEMETRY_DATA_DIR")
            .map(PathBuf::from)
            .unwrap_or_else(|| root.join("mock_data"));
        let ticket_path = env::var_os("OPS_TELEMETRY_TICKET_PATH")
            .map(PathBuf::from)
            .unwrap_or_else(|| root.join("database/incidents.db"));
        let reference_time = match env::var("OPS_TELEMETRY_REFERENCE_TIME") {
            Ok(value) => value,
            Err(env::VarError::NotPresent) => DEMO_REFERENCE_TIME.to_owned(),
            Err(error) => return Err(error.into()),
        };
        let reference_time = DateTime::parse_from_rfc3339(&reference_time)?.to_utc();
        Ok(Self {
            data: TelemetryData::load(&data_dir)?,
            reference_time,
            ticket_path,
            tool_router: Self::tool_router(),
        })
    }
}

#[tool_handler(router = self.tool_router)]
impl ServerHandler for TelemetryServer {
    fn get_info(&self) -> ServerConfig {
        let capabilities = ServerCapabilities::builder()
            .enable_tools()
            .enable_resources()
            .build();
        ServerConfig::new(capabilities)
            .with_server_info(Implementation::new(env!("CARGO_PKG_NAME"), env!("CARGO_PKG_VERSION")))
            .with_instructions("Query simulated staging telemetry and read operational guidance. Creating an incident ticket writes to local storage.")
    }

    async fn list_resources(
        &self,
        _request: Option<PaginatedRequestParams>,
        _context: RequestContext<RoleServer>,
    ) -> Result<ListResourcesResult, ErrorData> {
        Ok(ListResourcesResult::with_all_items(resources::list(
            &self.data,
        )))
    }

    async fn list_resource_templates(
        &self,
        _request: Option<PaginatedRequestParams>,
        _context: RequestContext<RoleServer>,
    ) -> Result<ListResourceTemplatesResult, ErrorData> {
        Ok(ListResourceTemplatesResult::with_all_items(vec![
            resources::runbook_template(),
        ]))
    }

    async fn read_resource(
        &self,
        request: ReadResourceRequestParams,
        _context: RequestContext<RoleServer>,
    ) -> Result<ReadResourceResponse, ErrorData> {
        let content = resources::read(&self.data, &request.uri)?;
        Ok(ReadResourceResponse::Complete(ReadResourceResult::new(
            vec![content],
        )))
    }
}
