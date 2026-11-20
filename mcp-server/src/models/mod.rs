use std::num::NonZeroU32;

use chrono::{DateTime, Utc};
use rmcp::schemars::{self, JsonSchema};
use serde::{Deserialize, Serialize};

#[derive(Clone, Copy, Deserialize, JsonSchema, PartialEq, Serialize)]
#[serde(rename_all = "UPPERCASE")]
pub(crate) enum LogSeverity {
    Info,
    Warn,
    Error,
    Fatal,
}

#[derive(Deserialize, Serialize)]
pub(crate) struct LogEntry {
    pub id: String,
    pub timestamp: DateTime<Utc>,
    pub service_name: String,
    pub severity: LogSeverity,
    pub event: String,
    pub message: String,
}

#[derive(Deserialize, Serialize)]
pub(crate) struct Deployment {
    pub deployment_id: String,
    pub service_name: String,
    pub version: String,
    pub commit_hash: String,
    pub timestamp: DateTime<Utc>,
    pub status: String,
    pub rollback_status: String,
    pub summary: String,
}

#[derive(Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub(crate) struct SearchLogs {
    /// Exact service name, such as payments-api.
    #[schemars(length(min = 1))]
    pub service_name: String,
    /// Exact severity to match.
    pub severity: LogSeverity,
    /// Maximum number of results, with a minimum of one.
    pub limit: NonZeroU32,
}

#[derive(Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub(crate) struct DeploymentHistory {
    /// Exact service name, such as payments-api.
    #[schemars(length(min = 1))]
    pub service_name: String,
    /// Positive number of hours ending at the mock staging reference time.
    pub window_hours: NonZeroU32,
}

#[derive(Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub(crate) struct CreateIncidentTicket {
    /// Short incident title.
    #[schemars(length(min = 1))]
    pub title: String,
    /// Non-blank incident severity label.
    #[schemars(length(min = 1))]
    pub severity: String,
    /// Symptoms, impact, and supporting evidence.
    #[schemars(length(min = 1))]
    pub summary: String,
    /// Team or person assigned to the incident.
    #[schemars(length(min = 1))]
    pub assignee: String,
}

#[derive(Serialize)]
pub(crate) struct IncidentTicket {
    pub ticket_id: String,
    pub created_at: DateTime<Utc>,
    pub title: String,
    pub severity: String,
    pub summary: String,
    pub assignee: String,
}

#[cfg(test)]
mod tests {
    use serde_json::json;

    use super::*;

    #[test]
    fn log_query_requires_the_declared_fields_and_severity() {
        for severity in ["INFO", "WARN", "ERROR", "FATAL"] {
            let query = serde_json::from_value::<SearchLogs>(json!({
                "service_name": "payments-api", "severity": severity, "limit": 10
            }))
            .unwrap();
            assert_eq!(query.limit.get(), 10);
        }
        for invalid in [
            json!({"service_name": "payments-api", "severity": "HIGH", "limit": 10}),
            json!({"service_name": "payments-api", "severity": "ERROR", "limit": 0}),
            json!({"service_name": "payments-api", "severity": "ERROR"}),
            json!({"service_name": "payments-api", "severity": "ERROR", "limit": 10, "extra": true}),
        ] {
            assert!(serde_json::from_value::<SearchLogs>(invalid).is_err());
        }
    }

    #[test]
    fn deployment_window_requires_a_positive_integer() {
        for invalid in [json!(0), json!(-1), json!(1.5), json!("24")] {
            assert!(
                serde_json::from_value::<DeploymentHistory>(json!({
                    "service_name": "payments-api", "window_hours": invalid
                }))
                .is_err()
            );
        }
    }

    #[test]
    fn ticket_input_requires_all_four_fields() {
        let example = json!({
            "title": "Payment API timeout",
            "severity": "HIGH",
            "summary": "Payment failures increased following deployment.",
            "assignee": "backend-team",
        });
        let ticket = serde_json::from_value::<CreateIncidentTicket>(example.clone()).unwrap();
        assert_eq!(ticket.severity, "HIGH");

        for field in ["title", "severity", "summary", "assignee"] {
            let mut incomplete = example.clone();
            incomplete.as_object_mut().unwrap().remove(field);
            assert!(serde_json::from_value::<CreateIncidentTicket>(incomplete).is_err());
        }
    }
}
