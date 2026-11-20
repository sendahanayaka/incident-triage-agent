# notification-worker runbook

The worker consumes queued notifications and sends them through a sandbox provider.

## Symptoms

- `delivery_retried` warnings appear after provider timeouts.
- Persistent failures may be accompanied by growing queue depth or a failing delivery smoke probe.

## Troubleshoot

1. Check whether `delivery_retried` warnings are followed by successful delivery. A recovered retry with a drained queue can be treated as transient.
2. Check queue depth, recent delivery failures, and the delivery smoke probe.
3. Compare sustained failures with any deployment that changed retry timing or provider settings.

## Escalate

Assign an incident to `messaging-oncall` if deliveries keep failing after retries or the queue grows across consecutive probes. Include the last successful delivery and the deployed version.

## Recovery

Allow the configured retry to run and verify that delivery succeeds and the queue drains. If warnings persist, have the on-call engineer verify provider health and review the retry configuration. Rerun the delivery smoke probe before clearing the release check.
