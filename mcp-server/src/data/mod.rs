pub(crate) mod tickets;

use std::{
    cmp::Reverse,
    collections::{BTreeMap, BTreeSet},
    fs,
    path::Path,
};

use serde::de::DeserializeOwned;

use crate::{
    errors::ServerError,
    models::{Deployment, LogEntry},
};

pub(crate) struct TelemetryData {
    pub logs: Vec<LogEntry>,
    pub deployments: Vec<Deployment>,
    pub runbooks: BTreeMap<String, String>,
    pub release_checklist: String,
}

impl TelemetryData {
    pub fn load(directory: &Path) -> Result<Self, ServerError> {
        let mut logs: Vec<LogEntry> = read_json(&directory.join("logs.json"))?;
        let mut deployments: Vec<Deployment> = read_json(&directory.join("deployments.json"))?;
        let release_checklist = read_text(&directory.join("release-checklist.md"))?;
        let services: BTreeSet<_> = logs
            .iter()
            .map(|entry| &entry.service_name)
            .chain(deployments.iter().map(|entry| &entry.service_name))
            .collect();

        let mut runbooks = BTreeMap::new();
        for service in services {
            if service.is_empty()
                || !service
                    .bytes()
                    .all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit() || byte == b'-')
            {
                return Err(ServerError::InvalidServiceName(service.clone()));
            }
            let path = directory.join("runbooks").join(format!("{service}.md"));
            runbooks.insert(service.clone(), read_text(&path)?);
        }

        logs.sort_by_key(|entry| Reverse(entry.timestamp));
        deployments.sort_by_key(|entry| Reverse(entry.timestamp));
        Ok(Self {
            logs,
            deployments,
            runbooks,
            release_checklist,
        })
    }
}

fn read_text(path: &Path) -> Result<String, ServerError> {
    fs::read_to_string(path).map_err(|source| ServerError::ReadFixture {
        path: path.to_owned(),
        source,
    })
}

fn read_json<T: DeserializeOwned>(path: &Path) -> Result<T, ServerError> {
    let contents = read_text(path)?;
    serde_json::from_str(&contents).map_err(|source| ServerError::ParseFixture {
        path: path.to_owned(),
        source,
    })
}
