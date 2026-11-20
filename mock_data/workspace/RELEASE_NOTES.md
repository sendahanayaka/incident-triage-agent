# Staging release notes

## payments-api 2.4.2

- Candidate deployment `pay-204` completed at 04:04 UTC on 2026-11-20.
- The candidate reduced the gateway timeout from 1000 ms to 250 ms.
- The service started, but the checkout smoke test failed with HTTP 504 responses. Promotion is blocked.
- The last known-good staging release is `2.4.1` (`pay-203`).

## auth-service 1.8.4

- Version `1.8.3` returned HTTP 401 for fresh tokens after a staging signing-key rotation left the local cache stale.
- Deployment `auth-087` refreshed the signing-key cache. The health probe and three consecutive fresh-token smoke probes passed afterward.
- The fallback version is `1.8.3`. A rollback requires a cache refresh and passing fresh-token smoke probes before promotion.

## notification-worker 3.1.2

- Deployment `notify-116` updated the transient delivery retry delay.
- The health probe and delivery smoke test passed. The queue drained after retries.
- The known-good rollback version is `3.1.1`.
