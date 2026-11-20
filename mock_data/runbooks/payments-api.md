# payments-api runbook

The service authorizes staging checkout payments through a sandbox gateway.

## Symptoms

- Authorization requests return HTTP 504 and the checkout smoke test fails.
- Staging logs show repeated `gateway_timeout` events after a deployment.

## Troubleshoot

1. Check ERROR and FATAL logs for repeated `gateway_timeout` events, HTTP 504 responses, or failed checkout smoke tests.
2. Compare the first failure timestamp with deployment history. Inspect changes to the gateway timeout in the candidate.
3. Compare the configured timeout with observed gateway response time and the configuration limits. A gateway response slower than the configured timeout can account for HTTP 504 responses.

## Escalate

Assign an incident to `payments-oncall` if three consecutive authorization probes fail or the checkout smoke test reports a FATAL event. Include the candidate version, deployment ID, and evidence from the gateway logs.

## Recovery

Ask the on-call engineer to restore the last known-good timeout or review a rollback to the previous release. Keep promotion blocked until the corrected configuration meets the documented minimum and the checkout smoke test passes.
