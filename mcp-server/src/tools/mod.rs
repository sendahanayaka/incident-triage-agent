use chrono::{DateTime, TimeDelta, Utc};
use rmcp::{handler::server::wrapper::Parameters, model::CallToolResult, tool, tool_router};
use serde_json::json;

use crate::{
    data::tickets,
    errors,
    models::{CreateIncidentTicket, DeploymentHistory, SearchLogs},
    server::TelemetryServer,
};

#[tool_router(vis = "pub(crate)")]
impl TelemetryServer {
    #[tool(
        description = "Find the newest mock log entries for an exact service name and severity. Returns up to limit records.",
        annotations(read_only_hint = true, open_world_hint = false)
    )]
    fn search_logs(&self, Parameters(input): Parameters<SearchLogs>) -> CallToolResult {
        if !self.data.runbooks.contains_key(&input.service_name) {
            return errors::unknown_service(&input.service_name);
        }
        let logs: Vec<_> = self
            .data
            .logs
            .iter()
            .filter(|entry| {
                entry.service_name == input.service_name && entry.severity == input.severity
            })
            .take(input.limit.get() as usize)
            .collect();
        CallToolResult::structured(json!({ "logs": logs }))
    }

    #[tool(
        description = "List newest-first deployments for an exact service within the requested hours before the mock reference time, including commit hashes, UTC timestamps, and rollback statuses.",
        annotations(read_only_hint = true, open_world_hint = false)
    )]
    fn get_deployment_history(
        &self,
        Parameters(input): Parameters<DeploymentHistory>,
    ) -> CallToolResult {
        if !self.data.runbooks.contains_key(&input.service_name) {
            return errors::unknown_service(&input.service_name);
        }
        let window_end = self.reference_time;
        let window_start = window_end
            .checked_sub_signed(TimeDelta::hours(i64::from(input.window_hours.get())))
            .unwrap_or(DateTime::<Utc>::MIN_UTC);
        let deployments: Vec<_> = self
            .data
            .deployments
            .iter()
            .filter(|entry| {
                entry.service_name == input.service_name
                    && (window_start..=window_end).contains(&entry.timestamp)
            })
            .collect();
        CallToolResult::structured(json!({
            "deployments": deployments,
            "window_start": window_start,
            "window_end": window_end,
        }))
    }

    #[tool(
        description = "Save an incident ticket in the local SQLite database and return the saved ticket. Call only after the user has approved the proposed ticket.",
        annotations(
            read_only_hint = false,
            destructive_hint = false,
            idempotent_hint = false,
            open_world_hint = false
        )
    )]
    async fn create_incident_ticket(
        &self,
        Parameters(input): Parameters<CreateIncidentTicket>,
    ) -> CallToolResult {
        for (field, value) in [
            ("title", &input.title),
            ("severity", &input.severity),
            ("summary", &input.summary),
            ("assignee", &input.assignee),
        ] {
            if value.trim().is_empty() {
                return errors::blank_ticket_field(field);
            }
        }

        let path = self.ticket_path.clone();
        match tokio::task::spawn_blocking(move || tickets::save_ticket(&path, input)).await {
            Ok(Ok(ticket)) => CallToolResult::structured(json!(ticket)),
            Ok(Err(error)) => errors::ticket_storage_error(error),
            Err(error) => errors::ticket_storage_error(error),
        }
    }
}
