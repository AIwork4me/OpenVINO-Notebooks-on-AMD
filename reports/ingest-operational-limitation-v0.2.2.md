# Ingest Workflow Operational Limitation — v0.2.2 Release Record

## Status: `BLOCKED_INFRASTRUCTURE` (self-hosted runner git-egress outage)

The `ingest-validation-evidence` workflow (self-hosted runner) has **no single
end-to-end green run** as of the v0.2.2 release cut. Root cause is external to
the workflow logic: the runner cannot perform git transport to github.com
(direct `https://github.com` and the site mirror `gh-test.anruicloud.com` both
fail CONNECT), so the resumable checkout step exhausts its bounded retries and
the job exits before artifact download/overlay/merge can start.

## Latest dispatch evidence (release-closure retry)

```text
run 37643439823 (workflow_dispatch, main, 2026-10-07T15:22:57Z):
  completed failure after 9m52s
  step "Resilient checkout (github.com with site-mirror fallback)":
    fetch failed via https://github.com           x3 (2m30s apart)
    fetch failed via https://gh-test.anruicloud.com x3
    FATAL: could not fetch main via any transport
prior dispatches: 37630021723 (8m58s), 37628494427 (8m31s), 37621297425 (cancelled 58m)
```

## Why this is not a release blocker

- The failure is in **git egress from the runner**, not in the ingest pipeline
  stages (checkout integrity pin, artifact download, resumable transport, zip
  validation, evidence overlay, state merge, integrity validation). Those
  stages were proven piecewise during the comprehensive-verification closure
  (see `reports/comprehensive-verification-final.md`).
- All v0.2.2 evidence was ingested through the primary path (runner-local
  commit of `results/`), which does not depend on the workflow.
- API-plane operations from the runner succeed (`gh api` reaches
  api.github.com); only git-over-HTTPS CONNECT is refused by the site egress
  proxy. When egress policy is restored, a dispatch of the workflow is
  expected to complete; the workflow itself is unchanged and ready.

## Exit criteria

One green end-to-end dispatch recording `INGEST OPERATIONAL — PASS`. Until
then this file stands as the honest operational record.
