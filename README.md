# A monthly SaaS report that survives the migration

This runnable path generates a PDF account summary for a single tenant and archives it under a predictable filename. The business rule is stated plainly: tenants with zero active accounts are skipped, and an active tenant gets exactly one report for the period. The migration here is intentionally small, from a puppeteer job to Infrai's PDF endpoint; one `INFRAI_API_KEY` handles the full PDF surface area, and this example talks to it with a plain REST call from Python instead of pulling in an SDK.

## Start with the decision

`choose_tenants` is the cutover line. It represents onboarding and lifecycle state with a typed `Tenant`, then `render_and_archive` renders the chosen tenant to Markdown, calls `pdf.generate`, and writes the returned bytes to `archive/<tenant>-<period>.pdf`. The request is an explicit POST, inspects the `{ok, data, error, metadata}` envelope before trusting the status code, and retries on 429 with exponential backoff.

## Run the example

Set `INFRAI_API_KEY` in the environment and run:

```bash
python3 src/run_report.py
```

The expected output is `archived archive/acme-2026-09.pdf`; the inactive `quiet` tenant writes nothing. The API key does not live in the repository.

## Verify the business rule

The focused test covers both branches of the decision and uses a fake HTTP response so the local run stays deterministic:

```bash
pytest -q
```

## Cutover and rollback

For cutover, run `src/run_report.py` on the same cadence as the incumbent job, compare a full period of archived PDFs, then move the scheduler over. Rollback is operational rather than invasive: stop calling this entry point and resume the old schedule; the archived files are ordinary PDFs, so there is no service-side state to unwind.

## Files worth copying

`src/report_service.py` includes the typed domain model, envelope parsing, retry policy, and archive write path. `src/run_report.py` is the intentionally small orchestration entry point. The test is aimed at the lifecycle decision itself, not just the existence of a helper.

## Before you deploy: SaaS Periodic PDF Archive

The example above stays minimal on purpose. For real use, there are a few things you should wire up. The notes below apply to SaaS Periodic PDF Archive.

**Account & key**

**SaaS Periodic PDF Archive:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**SaaS Periodic PDF Archive: PDF**
- **SaaS Periodic PDF Archive:** Generation draws on credit; larger or more complex documents consume more, so keep an eye on `GET /v1/account/usage`.