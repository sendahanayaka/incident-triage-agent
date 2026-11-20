use std::{fs, io, path::Path, time::Duration};

use chrono::{SecondsFormat, Utc};
use rusqlite::{Connection, TransactionBehavior, params};
use thiserror::Error;

use crate::models::{CreateIncidentTicket, IncidentTicket};

#[derive(Debug, Error)]
pub(crate) enum TicketStoreError {
    #[error("could not create the database directory: {0}")]
    Directory(#[from] io::Error),
    #[error("SQLite ticket store: {0}")]
    Database(#[from] rusqlite::Error),
    #[error("incident ticket IDs exhausted")]
    IdExhausted,
}

pub(crate) fn save_ticket(
    path: &Path,
    details: CreateIncidentTicket,
) -> Result<IncidentTicket, TicketStoreError> {
    if let Some(parent) = path
        .parent()
        .filter(|parent| !parent.as_os_str().is_empty())
    {
        fs::create_dir_all(parent)?;
    }
    let mut connection = Connection::open(path)?;
    connection.busy_timeout(Duration::from_secs(3))?;
    insert_ticket(&mut connection, details)
}

fn insert_ticket(
    connection: &mut Connection,
    details: CreateIncidentTicket,
) -> Result<IncidentTicket, TicketStoreError> {
    let transaction = connection.transaction_with_behavior(TransactionBehavior::Immediate)?;
    transaction.execute_batch(
        "CREATE TABLE IF NOT EXISTS incident_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            title TEXT NOT NULL,
            severity TEXT NOT NULL,
            summary TEXT NOT NULL,
            assignee TEXT NOT NULL
        );",
    )?;
    let created_at = Utc::now();
    let timestamp = created_at.to_rfc3339_opts(SecondsFormat::AutoSi, true);
    let id: i64 = transaction.query_row(
        "INSERT INTO incident_tickets (created_at, title, severity, summary, assignee)
         VALUES (?1, ?2, ?3, ?4, ?5)
         RETURNING id",
        params![
            timestamp,
            details.title,
            details.severity,
            details.summary,
            details.assignee
        ],
        |row| row.get(0),
    )?;
    let number = id.checked_add(1041).ok_or(TicketStoreError::IdExhausted)?;
    transaction.commit()?;

    Ok(IncidentTicket {
        ticket_id: format!("INC-{number}"),
        created_at,
        title: details.title,
        severity: details.severity,
        summary: details.summary,
        assignee: details.assignee,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn incident() -> CreateIncidentTicket {
        CreateIncidentTicket {
            title: "Payment API timeout".to_owned(),
            severity: "HIGH".to_owned(),
            summary: "The staging gateway exceeded its timeout.".to_owned(),
            assignee: "backend-team".to_owned(),
        }
    }

    #[test]
    fn inserts_all_fields_into_sqlite() {
        let mut db = Connection::open_in_memory().unwrap();
        let ticket = insert_ticket(&mut db, incident()).unwrap();
        let stored: (String, String, String, String, String) = db
            .query_row(
                "SELECT created_at, title, severity, summary, assignee FROM incident_tickets",
                [],
                |row| {
                    Ok((
                        row.get(0)?,
                        row.get(1)?,
                        row.get(2)?,
                        row.get(3)?,
                        row.get(4)?,
                    ))
                },
            )
            .unwrap();

        assert_eq!(ticket.ticket_id, "INC-1042");
        assert_eq!(
            chrono::DateTime::parse_from_rfc3339(&stored.0).unwrap(),
            ticket.created_at
        );
        assert_eq!(
            (stored.1, stored.2, stored.3, stored.4),
            (
                ticket.title,
                ticket.severity,
                ticket.summary,
                ticket.assignee
            )
        );
    }

    #[test]
    fn rolls_back_an_insert_if_ticket_id_generation_fails() {
        let mut db = Connection::open_in_memory().unwrap();
        insert_ticket(&mut db, incident()).unwrap();
        db.execute(
            "UPDATE sqlite_sequence SET seq = ?1 WHERE name = 'incident_tickets'",
            [i64::MAX - 1041],
        )
        .unwrap();

        let result = insert_ticket(&mut db, incident());

        assert!(matches!(result, Err(TicketStoreError::IdExhausted)));
        let count: i64 = db
            .query_row("SELECT count(*) FROM incident_tickets", [], |row| {
                row.get(0)
            })
            .unwrap();
        assert_eq!(count, 1);
    }
}
