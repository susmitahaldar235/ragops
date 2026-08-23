# Governance and review

`ragops governance` stores artifact digests, lifecycle state, append-only reviews, waivers, and audit events in local SQLite. The valid lifecycle is `draft -> reviewed -> accepted -> superseded`; acceptance requires an approval review.

Reviewer-specific queues hide candidate/provider metadata until that reviewer votes. This reduces anchoring bias but is not a substitute for access control: protect the database with normal filesystem controls. Verify the referenced evidence bundle before accepting an artifact.

```bash
ragops governance register --store .ragops/governance.db \
  --artifact-id release-2026-08-23 --kind release-decision \
  --digest "$SHA256" --metadata public.json --blinded-metadata candidate.json --actor ci
ragops governance transition --store .ragops/governance.db \
  --artifact-id release-2026-08-23 --state reviewed --actor owner
ragops governance queue --store .ragops/governance.db --reviewer alice
ragops governance review --store .ragops/governance.db \
  --artifact-id release-2026-08-23 --reviewer alice --verdict approve
```
