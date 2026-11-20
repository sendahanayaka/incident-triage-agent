# Staging release checklist

1. Match the service and candidate version across the release notes, service configuration, service manifest, and deployment history.
2. Verify the candidate's health probe and service-specific smoke test both passed.
3. Check for unresolved ERROR or FATAL events since the candidate deployment. Any unresolved release-related failure blocks promotion.
4. Verify the candidate configuration meets documented limits and a known-good rollback version is identified.
5. Mark the release ready only when all checks have supporting evidence. Report failed or unverified checks with the next action needed.
