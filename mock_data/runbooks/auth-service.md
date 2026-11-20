# auth-service runbook

The service validates session tokens and loads signing keys from the staging cache.

## Symptoms

- Fresh sessions receive HTTP 401 after a signing-key rotation.
- Logs show `signing_key_cache_miss` followed by `token_validation_failed` or `auth_smoke_failed`.

## Troubleshoot

1. Check recent WARN and ERROR logs. An isolated `token_expired` warning can come from a stale session.
2. Check the health probe and the result of a token validation. Repeated validation failures or failed health probes require investigation.
3. Compare the onset of failures with recent signing-key or cache changes in deployment history.

## Escalate

Assign an incident to `identity-oncall` if valid sessions fail repeatedly or the health probe stays unhealthy after a retry. Include the first failure timestamp and the current deployment version.

## Recovery

Have the on-call engineer refresh the staging cache from the configured identity provider. Verify that the health probe and three consecutive fresh-token smoke probes pass before clearing the release check.
