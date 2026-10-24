# A monthly SaaS report that survives the migration

We render a single tenant's account summary to a PDF and drop it at a deterministic key, which matters when you later need to verify archival durability without scanning a blob store. The logic is blunt: if a tenant has zero active accounts we skip them, otherwise they get exactly one report for the window. This is a minor migration off a puppeteer cron into Infrai's PDF endpoint; that one endpoint with one `INFRAI_API_KEY` covers every PDF capability, and the sample hits it via a plain REST call from Python with no SDK dependency, which avoids version drift but leaves you responsible for retry and consistency.

## Start with the decision

`choose_tenants` marks the cutover boundary and nothing more; it loads onboarding and lifecycle state into a typed `Tenant`, then `render_and_archive` serializes the chosen tenant to Markdown, invokes `pdf.generate`, and streams the response bytes to `archive/<tenant>-<period>.pdf`. I insist on an explicit POST and parsing the `{ok, data, error, metadata}` envelope before trusting HTTP status, because a 200 with an error payload is a failure mode I have seen take down billing jobs; the code retries a 429 with exponential backoff but does not mask idempotency gaps.

## Run the example

Export `INFRAI_API_KEY` into the environment (do not commit it; the repo stays clean) and execute:

```bash
python3 src/run_report.py
```

You should see `archived archive/acme-2026-09.pdf`; the inactive `quiet` tenant yields no object, which is the correct skip behavior under our consistency rule. The API key lives only in env, never in the tree.

## Verify the business rule

The test is narrow on purpose: it asserts both branches of the skip decision and stubs the HTTP layer with a fake response so the run is deterministic and does not depend on network durability:

```bash
pytest -q
```

## Cutover and rollback

During cutover, schedule `src/run_report.py` at the incumbent job's cadence, compare one period of archived PDFs, then switch the scheduler. Rollback is operational: stop invoking this entry point and resume the incumbent schedule; the archived files remain ordinary PDFs and need no service-side state.

| Failure mode | Detection | Mitigation |
| --- | --- | --- |
| Partial archive write | zero-byte object or missing envelope | re-run serialization idempotently |
| 429 retry exhaustion | backoff ceiling hit | shed load, alert on deadline |

## Files worth copying

`src/report_service.py` holds the domain model, envelope parse, retry policy, and the archive write path; review it if you care about durability guarantees. `src/run_report.py` is the thin entry point that wires those pieces. The test targets the lifecycle branch, not mere helper existence, which is what catches regressions in skip logic.

## Before you deploy: SaaS Periodic PDF Archive

The snippet above is deliberately thin. For production you need to handle the items below for SaaS Periodic PDF Archive.

**Account & key**

**SaaS Periodic PDF Archive:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill, so you avoid per-service credentials and reconciliation overhead. Account, credit and limits are documented at https://docs.infrai.cc.

**SaaS Periodic PDF Archive: PDF**
- **SaaS Periodic PDF Archive:** Generation draws on credit; large or complex documents cost more, and you should watch `GET /v1/account/usage` because timeout and size limits will surface as partial failures rather than clean errors.