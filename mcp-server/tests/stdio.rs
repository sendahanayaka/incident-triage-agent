use std::{collections::BTreeSet, fs, path::Path, time::Duration};

use rmcp::{
    RoleClient, ServiceExt,
    model::{CallToolRequestParams, CallToolResult, ErrorCode, ReadResourceRequestParams},
    service::{RunningService, ServiceError},
    transport::TokioChildProcess,
};
use serde_json::{Value, json};
use tempfile::tempdir;
use tokio::{process::Command, time::timeout};

const SERVER: &str = env!("CARGO_BIN_EXE_ops-telemetry-mcp");
const DEADLINE: Duration = Duration::from_secs(10);
type Client = RunningService<RoleClient, ()>;

fn repo_root() -> &'static Path {
    Path::new(concat!(env!("CARGO_MANIFEST_DIR"), "/.."))
}

async fn connect(ticket_path: &Path, reference_time: Option<&str>) -> Client {
    let mut command = Command::new(SERVER);
    command
        .current_dir(repo_root())
        .env("OPS_TELEMETRY_TICKET_PATH", ticket_path)
        .env_remove("OPS_TELEMETRY_DATA_DIR")
        .env_remove("OPS_TELEMETRY_REFERENCE_TIME");
    if let Some(time) = reference_time {
        command.env("OPS_TELEMETRY_REFERENCE_TIME", time);
    }
    let transport = TokioChildProcess::new(command).unwrap();
    timeout(DEADLINE, ().serve(transport))
        .await
        .expect("MCP initialization timed out")
        .expect("MCP initialization failed")
}

async fn call(
    client: &Client,
    name: &str,
    arguments: Value,
) -> Result<CallToolResult, ServiceError> {
    let request = CallToolRequestParams::new(name.to_owned())
        .with_arguments(arguments.as_object().unwrap().clone());
    timeout(DEADLINE, client.call_tool(request))
        .await
        .expect("MCP tool call timed out")
}

fn payload(result: CallToolResult) -> Value {
    assert_ne!(result.is_error, Some(true), "{result:?}");
    result.structured_content.expect("structured tool output")
}

fn assert_mcp_error(error: ServiceError, code: ErrorCode, message_contains: &str) {
    let ServiceError::McpError(error) = error else {
        panic!("expected an MCP error, got {error:?}");
    };
    assert_eq!(error.code, code);
    assert!(error.message.contains(message_contains), "{error:?}");
}

#[tokio::test]
async fn initializes_and_discovers_tools_with_strict_schemas() {
    let dir = tempdir().unwrap();
    let client = connect(&dir.path().join("incidents.db"), None).await;
    let peer = client.peer_info().unwrap();
    assert_eq!(peer.server_info.as_ref().unwrap().name, "ops-telemetry-mcp");
    assert!(peer.capabilities.tools.is_some());
    assert!(peer.capabilities.resources.is_some());

    let tools = client.list_all_tools().await.unwrap();
    let expected = [
        (
            "search_logs",
            vec!["limit", "service_name", "severity"],
            true,
        ),
        (
            "get_deployment_history",
            vec!["service_name", "window_hours"],
            true,
        ),
        (
            "create_incident_ticket",
            vec!["assignee", "severity", "summary", "title"],
            false,
        ),
    ];
    assert_eq!(tools.len(), expected.len());
    for (name, required, read_only) in expected {
        let tool = tools.iter().find(|tool| tool.name == name).unwrap();
        assert_eq!(tool.input_schema["additionalProperties"], false);
        assert_eq!(
            tool.input_schema["required"]
                .as_array()
                .unwrap()
                .iter()
                .map(|name| name.as_str().unwrap())
                .collect::<BTreeSet<_>>(),
            required.into_iter().collect(),
        );
        assert_eq!(
            tool.annotations.as_ref().unwrap().read_only_hint,
            Some(read_only)
        );
        assert!(!tool.description.as_ref().unwrap().is_empty());
    }
    let search = tools
        .iter()
        .find(|tool| tool.name == "search_logs")
        .unwrap();
    assert_eq!(
        search.input_schema["properties"]["limit"]["type"],
        "integer"
    );
    let severity_schema = &search.input_schema["properties"]["severity"];
    let severity_definition = severity_schema["$ref"]
        .as_str()
        .and_then(|reference| reference.rsplit('/').next())
        .map(|name| &search.input_schema["$defs"][name])
        .unwrap_or(severity_schema);
    assert_eq!(
        severity_definition["enum"],
        json!(["INFO", "WARN", "ERROR", "FATAL"])
    );
    client.cancel().await.unwrap();
}

#[tokio::test]
async fn filters_logs_newest_first_and_keeps_log_messages_as_text() {
    let dir = tempdir().unwrap();
    let client = connect(&dir.path().join("incidents.db"), None).await;
    let result = payload(
        call(
            &client,
            "search_logs",
            json!({
                "service_name": "payments-api", "severity": "ERROR", "limit": 2
            }),
        )
        .await
        .unwrap(),
    );
    let logs = result["logs"].as_array().unwrap();
    assert_eq!(logs.len(), 2);
    assert_eq!(logs[0]["id"], "LOG-031");
    assert_eq!(logs[1]["id"], "LOG-028");
    assert!(
        logs.iter()
            .all(|log| log["service_name"] == "payments-api" && log["severity"] == "ERROR")
    );

    let all_errors = payload(
        call(
            &client,
            "search_logs",
            json!({
                "service_name": "payments-api", "severity": "ERROR", "limit": 100
            }),
        )
        .await
        .unwrap(),
    );
    let seeded_log = all_errors["logs"]
        .as_array()
        .unwrap()
        .iter()
        .find(|log| log["id"] == "LOG-019")
        .unwrap();
    assert!(
        seeded_log["message"]
            .as_str()
            .unwrap()
            .contains("Ignore previous instructions")
    );
    assert!(!dir.path().join("incidents.db").exists());

    let empty = payload(
        call(
            &client,
            "search_logs",
            json!({
                "service_name": "notification-worker", "severity": "FATAL", "limit": 5
            }),
        )
        .await
        .unwrap(),
    );
    assert_eq!(empty["logs"], json!([]));
    client.cancel().await.unwrap();
}

#[tokio::test]
async fn filters_deployments_by_service_and_inclusive_time_window() {
    let dir = tempdir().unwrap();
    let ticket_path = dir.path().join("incidents.db");
    let client = connect(&ticket_path, None).await;
    let query =
        |window_hours| json!({"service_name": "payments-api", "window_hours": window_hours});
    let recent = payload(
        call(&client, "get_deployment_history", query(1))
            .await
            .unwrap(),
    );
    assert_eq!(recent["window_start"], "2026-11-20T03:30:00Z");
    assert_eq!(recent["window_end"], "2026-11-20T04:30:00Z");
    assert_eq!(recent["deployments"].as_array().unwrap().len(), 1);
    assert_eq!(recent["deployments"][0]["deployment_id"], "pay-204");
    assert_eq!(recent["deployments"][0]["rollback_status"], "not_requested");
    assert_eq!(
        recent["deployments"][0]["commit_hash"]
            .as_str()
            .unwrap()
            .len(),
        40
    );
    let wider = payload(
        call(&client, "get_deployment_history", query(2))
            .await
            .unwrap(),
    );
    assert_eq!(wider["deployments"][0]["deployment_id"], "pay-204");
    assert_eq!(wider["deployments"][1]["deployment_id"], "pay-203");
    assert_eq!(wider["deployments"].as_array().unwrap().len(), 2);
    client.cancel().await.unwrap();

    let offset_client = connect(&ticket_path, Some("2026-11-20T09:50:00+05:30")).await;
    let boundary = payload(
        call(&offset_client, "get_deployment_history", query(1))
            .await
            .unwrap(),
    );
    assert_eq!(boundary["window_start"], "2026-11-20T03:20:00Z");
    assert_eq!(boundary["deployments"][1]["deployment_id"], "pay-203");
    offset_client.cancel().await.unwrap();

    let earlier_client = connect(&ticket_path, Some("2026-11-20T03:20:00Z")).await;
    let earlier = payload(
        call(&earlier_client, "get_deployment_history", query(1))
            .await
            .unwrap(),
    );
    assert_eq!(earlier["deployments"].as_array().unwrap().len(), 1);
    assert_eq!(earlier["deployments"][0]["deployment_id"], "pay-203");
    earlier_client.cancel().await.unwrap();
}

#[tokio::test]
async fn lists_and_reads_all_markdown_resources() {
    let dir = tempdir().unwrap();
    let client = connect(&dir.path().join("incidents.db"), None).await;
    let expected = [
        ("config://release-checklist", "Staging release checklist"),
        ("service://runbooks/auth-service", "identity-oncall"),
        ("service://runbooks/notification-worker", "messaging-oncall"),
        ("service://runbooks/payments-api", "payments-oncall"),
    ];
    let resources = client.list_all_resources().await.unwrap();
    assert_eq!(resources.len(), expected.len());
    for (uri, evidence) in expected {
        let entry = resources
            .iter()
            .find(|resource| resource.uri == uri)
            .unwrap();
        assert_eq!(entry.mime_type.as_deref(), Some("text/markdown"));
        let result = client
            .read_resource(ReadResourceRequestParams::new(uri))
            .await
            .unwrap();
        let content = serde_json::to_value(&result.contents[0]).unwrap();
        assert_eq!(content["uri"], uri);
        assert_eq!(content["mimeType"], "text/markdown");
        assert!(content["text"].as_str().unwrap().contains(evidence));
    }
    let templates = client.list_all_resource_templates().await.unwrap();
    assert_eq!(templates.len(), 1);
    assert_eq!(
        templates[0].uri_template,
        "service://runbooks/{service_name}"
    );

    let missing = client
        .read_resource(ReadResourceRequestParams::new(
            "service://runbooks/inventory-api",
        ))
        .await;
    assert_mcp_error(
        missing.unwrap_err(),
        ErrorCode::RESOURCE_NOT_FOUND,
        "Resource not found",
    );
    client.cancel().await.unwrap();
}

#[tokio::test]
async fn rejects_invalid_arguments_and_unknown_services_without_exiting() {
    let dir = tempdir().unwrap();
    let client = connect(&dir.path().join("incidents.db"), None).await;
    let invalid = [
        json!({"service_name": "payments-api", "severity": "INVALID", "limit": 1}),
        json!({"service_name": "payments-api", "severity": "ERROR", "limit": 0}),
        json!({"service_name": "payments-api", "severity": "ERROR", "limit": "1"}),
        json!({"service_name": "payments-api", "severity": "ERROR"}),
        json!({"service_name": "payments-api", "severity": "ERROR", "limit": 1, "extra": true}),
    ];
    for arguments in invalid {
        let result = call(&client, "search_logs", arguments).await.unwrap();
        assert_eq!(result.is_error, Some(true));
        assert!(
            result.content[0]
                .as_text()
                .unwrap()
                .text
                .contains("failed to deserialize parameters"),
        );
    }
    let invalid_window = call(
        &client,
        "get_deployment_history",
        json!({"service_name": "payments-api", "window_hours": -1}),
    )
    .await
    .unwrap();
    assert_eq!(invalid_window.is_error, Some(true));
    let requests = [
        (
            "search_logs",
            json!({"severity": "ERROR", "limit": 1, "service_name": "inventory-api"}),
        ),
        (
            "get_deployment_history",
            json!({"window_hours": 1, "service_name": "inventory-api"}),
        ),
    ];
    for (name, arguments) in requests {
        let result = call(&client, name, arguments).await.unwrap();
        assert_eq!(result.is_error, Some(true));
        let error = result.structured_content.unwrap();
        assert_eq!(error["code"], "unknown_service");
        assert_eq!(error["service_name"], "inventory-api");
    }
    assert_eq!(client.list_all_tools().await.unwrap().len(), 3);
    client.cancel().await.unwrap();
}

fn incident(title: &str) -> Value {
    json!({
        "title": title,
        "severity": "HIGH",
        "summary": "Checkout smoke tests failed after pay-204.",
        "assignee": "payments-oncall",
    })
}

#[tokio::test]
async fn validates_and_persists_tickets_across_concurrent_server_processes() {
    let dir = tempdir().unwrap();
    let path = dir.path().join("nested").join("incidents.db");
    let client = connect(&path, None).await;
    let blank = call(&client, "create_incident_ticket", incident("  "))
        .await
        .unwrap();
    assert_eq!(blank.is_error, Some(true));
    assert_eq!(blank.structured_content.unwrap()["field"], "title");
    assert!(!path.exists());
    let first = payload(
        call(
            &client,
            "create_incident_ticket",
            incident("Payments unavailable"),
        )
        .await
        .unwrap(),
    );
    assert_eq!(first["ticket_id"], "INC-1042");
    client.cancel().await.unwrap();

    let one = connect(&path, None).await;
    let two = connect(&path, None).await;
    let (one_result, two_result) = tokio::join!(
        call(&one, "create_incident_ticket", incident("First follow-up")),
        call(&two, "create_incident_ticket", incident("Second follow-up")),
    );
    let one_result = payload(one_result.unwrap());
    let two_result = payload(two_result.unwrap());
    let ids = [
        one_result["ticket_id"].as_str().unwrap(),
        two_result["ticket_id"].as_str().unwrap(),
    ];
    assert_eq!(
        BTreeSet::from(ids),
        BTreeSet::from(["INC-1043", "INC-1044"])
    );
    let db =
        rusqlite::Connection::open_with_flags(&path, rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY)
            .unwrap();
    let count: i64 = db
        .query_row("SELECT count(*) FROM incident_tickets", [], |row| {
            row.get(0)
        })
        .unwrap();
    assert_eq!(count, 3);
    let stored = db.query_row(
        "SELECT created_at, title, severity, summary, assignee FROM incident_tickets WHERE id = 1",
        [],
        |row| Ok(json!({
            "ticket_id": "INC-1042",
            "created_at": row.get::<_, String>(0)?,
            "title": row.get::<_, String>(1)?,
            "severity": row.get::<_, String>(2)?,
            "summary": row.get::<_, String>(3)?,
            "assignee": row.get::<_, String>(4)?,
        })),
    ).unwrap();
    assert_eq!(first, stored);
    assert_eq!(first["title"], "Payments unavailable");
    assert_eq!(first["severity"], "HIGH");
    assert_eq!(
        first["summary"],
        "Checkout smoke tests failed after pay-204."
    );
    assert_eq!(first["assignee"], "payments-oncall");
    assert!(first["created_at"].as_str().unwrap().ends_with('Z'));
    drop(db);
    one.cancel().await.unwrap();
    two.cancel().await.unwrap();
}

#[tokio::test]
async fn reports_storage_failure_and_preserves_existing_bytes() {
    let dir = tempdir().unwrap();
    let path = dir.path().join("incidents.db");
    fs::write(&path, "invalid SQLite data").unwrap();
    let client = connect(&path, None).await;
    let result = call(
        &client,
        "create_incident_ticket",
        incident("Payments unavailable"),
    )
    .await
    .unwrap();
    assert_eq!(result.is_error, Some(true));
    assert_eq!(
        result.structured_content.unwrap()["code"],
        "ticket_storage_error"
    );
    assert_eq!(fs::read_to_string(&path).unwrap(), "invalid SQLite data");
    assert_eq!(client.list_all_tools().await.unwrap().len(), 3);
    client.cancel().await.unwrap();
}

#[test]
fn missing_fixtures_fail_on_stderr_without_corrupting_stdio() {
    let dir = tempdir().unwrap();
    let output = std::process::Command::new(SERVER)
        .current_dir(repo_root())
        .env("OPS_TELEMETRY_DATA_DIR", dir.path())
        .env_remove("OPS_TELEMETRY_REFERENCE_TIME")
        .output()
        .unwrap();
    assert!(!output.status.success());
    assert!(output.stdout.is_empty());
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        stderr.contains("could not read fixture") && stderr.contains("logs.json"),
        "{stderr}"
    );
}
