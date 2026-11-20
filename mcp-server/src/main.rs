mod data;
mod errors;
mod models;
mod resources;
mod server;
mod tools;

use std::process::ExitCode;

use rmcp::{ServiceExt, transport::stdio};
use server::TelemetryServer;

#[tokio::main]
async fn main() -> ExitCode {
    match run().await {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("ops-telemetry-mcp: {error}");
            ExitCode::FAILURE
        }
    }
}

async fn run() -> Result<(), Box<dyn std::error::Error>> {
    let server = TelemetryServer::from_environment()?;
    let service = server.serve(stdio()).await?;
    service.waiting().await?;
    Ok(())
}
