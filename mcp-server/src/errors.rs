use std::{io, path::PathBuf};

use rmcp::{ErrorData, model::CallToolResult};
use serde_json::json;
use thiserror::Error;

#[derive(Debug, Error)]
pub(crate) enum ServerError {
    #[error("could not read fixture {path}: {source}")]
    ReadFixture { path: PathBuf, source: io::Error },
    #[error("invalid JSON in fixture {path}: {source}")]
    ParseFixture {
        path: PathBuf,
        source: serde_json::Error,
    },
    #[error("invalid service name in telemetry fixtures: {0:?}")]
    InvalidServiceName(String),
    #[error("OPS_TELEMETRY_REFERENCE_TIME must be an RFC 3339 timestamp: {0}")]
    ReferenceTime(#[from] chrono::ParseError),
    #[error("could not access OPS_TELEMETRY_REFERENCE_TIME: {0}")]
    ReferenceTimeEnvironment(#[from] std::env::VarError),
}

pub(crate) fn unknown_service(service_name: &str) -> CallToolResult {
    CallToolResult::structured_error(json!({
        "code": "unknown_service",
        "message": format!("Unknown service {service_name:?}."),
        "service_name": service_name,
    }))
}

pub(crate) fn blank_ticket_field(field: &str) -> CallToolResult {
    CallToolResult::structured_error(json!({
        "code": "invalid_argument",
        "message": format!("{field} must contain a non-whitespace character."),
        "field": field,
    }))
}

pub(crate) fn ticket_storage_error(error: impl std::fmt::Display) -> CallToolResult {
    eprintln!("could not save incident ticket: {error}");
    CallToolResult::structured_error(json!({
        "code": "ticket_storage_error",
        "message": "Could not save the incident ticket.",
    }))
}

pub(crate) fn unknown_resource(uri: &str) -> ErrorData {
    ErrorData::resource_not_found("Resource not found.", Some(json!({ "uri": uri })))
}
