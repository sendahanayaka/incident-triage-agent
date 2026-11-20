use rmcp::{
    ErrorData,
    model::{Resource, ResourceContents, ResourceTemplate},
};

use crate::{data::TelemetryData, errors};

const CHECKLIST_URI: &str = "config://release-checklist";
const RUNBOOK_PREFIX: &str = "service://runbooks/";
const RUNBOOK_TEMPLATE: &str = "service://runbooks/{service_name}";
const MARKDOWN: &str = "text/markdown";

pub(crate) fn list(data: &TelemetryData) -> Vec<Resource> {
    let checklist = Resource::new(CHECKLIST_URI, "release-checklist")
        .with_description("Mandatory staging release verification criteria.")
        .with_mime_type(MARKDOWN);
    let runbooks = data.runbooks.keys().map(|service| {
        Resource::new(
            format!("{RUNBOOK_PREFIX}{service}"),
            format!("{service}-runbook"),
        )
        .with_description(format!(
            "Troubleshooting and escalation guidance for {service}."
        ))
        .with_mime_type(MARKDOWN)
    });
    std::iter::once(checklist).chain(runbooks).collect()
}

pub(crate) fn runbook_template() -> ResourceTemplate {
    ResourceTemplate::new(RUNBOOK_TEMPLATE, "service-runbook")
        .with_description("Markdown troubleshooting runbook for a known service.")
        .with_mime_type(MARKDOWN)
}

pub(crate) fn read(data: &TelemetryData, uri: &str) -> Result<ResourceContents, ErrorData> {
    let text = if uri == CHECKLIST_URI {
        &data.release_checklist
    } else {
        uri.strip_prefix(RUNBOOK_PREFIX)
            .and_then(|service| data.runbooks.get(service))
            .ok_or_else(|| errors::unknown_resource(uri))?
    };
    Ok(ResourceContents::text(text, uri).with_mime_type(MARKDOWN))
}
