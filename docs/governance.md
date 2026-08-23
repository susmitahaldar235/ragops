# Local governance workflow

The SQLite governance ledger keeps artifact digests, lifecycle state, append-only reviews, waivers, and audit events locally. Its state machine is `draft -> reviewed -> accepted -> superseded`; acceptance requires at least one approval.

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

Candidate/provider metadata stays hidden from each reviewer until that reviewer records a vote. The audit log and artifact/review update share the same SQLite transaction.
