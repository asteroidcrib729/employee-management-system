# CI and environment testing

Verification date: **2026-11-01**, Asia/Karachi. The launch commands are `uv run ems` for preview and `uv run ems production` for production. The old localhost `.env` is removed; the two private Azure runtime files remain.

## Automated repository checks

| Check | Trigger and purpose |
| --- | --- |
| Ruff lint and formatting | Every push and pull request; source, tests and scripts |
| Unit tests and coverage | Windows and Ubuntu; real isolated SQLite ORM fixtures, with an 85% branch-aware coverage gate |
| Repository validation | Python pin, syntax, duplicate YAML keys, workflow permissions, immutable action pins, private-file boundaries, local documentation links and original artifact hashes |
| Actionlint | Workflow syntax, expressions, action inputs and supported runner settings |
| Packaging | Locked build; Python/license metadata, LICENSE/NOTICE bytes, SQL resources, required docs and exclusion of secrets/local data |
| SQL Server integration | SQL Server 2022 Developer installed directly on GitHub's temporary Ubuntu runner; fresh setup, repeated seed, constraints and original-schema migration/rollback |
| Gitleaks | Full Git history plus a snapshot of publishable source; standard detectors and a database-password detector, with redacted output |
| Dependency audit | Runtime and development packages exported from the lock file and checked with pip-audit |
| Dependency review | Pull requests reject introduced vulnerable dependencies at low severity or above |
| CodeQL | Python and GitHub Actions analysis using the extended security queries |
| Dependabot | Weekly grouped updates for uv dependencies and GitHub Actions |

The security workflow also runs weekly and can be dispatched manually. Workflows default to read-only repository access; only CodeQL receives permission to upload security results. Actions use verified immutable commit SHAs. The Actionlint and Gitleaks installers verify pinned official release SHA-256 hashes before extracting a single executable. Dependabot updates action pins; standalone tool versions and checksums are maintained in `.github/ci-tools.json`.

The hosted runner installs SQL Server Developer directly from Microsoft's package repository, binds it to loopback, uses a freshly generated masked password and stops the service afterward. The runner is discarded by GitHub. Docker and a local SQL Server installation are not required. This follows Microsoft's [Ubuntu installation](https://learn.microsoft.com/en-us/sql/linux/install-upgrade/quickstart-install-ubuntu) and [network configuration](https://learn.microsoft.com/en-us/sql/linux/configure/mssql-conf) guidance. GitHub Actions receives no Azure passwords or access tokens and never targets the production/preview databases. No automatic merge or deployment is configured.

The source secret scanner includes untracked publishable files during local work. It builds a temporary snapshot using Git's tracked/non-ignored file list, leaving ignored local secrets outside the snapshot. Before scanning, it verifies that a generated nonfunctional password is detected and redacted. This is distinct from enabling GitHub's repository-level secret scanning/push protection settings.

## Reproduce local checks

Run from the repository root after installing Python 3.14.7, uv and the project's dependencies:

```powershell
uv sync --locked
uv lock --check
uv run ruff check .
uv run ruff format --check .
uv run coverage run -m unittest discover -s tests -v
uv run coverage report
uv run python scripts/validate_repository.py
uv build
uv run python scripts/validate_package.py
uv run python scripts/install_ci_tool.py actionlint
uv run python scripts/install_ci_tool.py gitleaks
.\.local\ci-tools\actionlint.exe
.\.local\ci-tools\gitleaks.exe git --redact --no-banner --log-opts=--all .
uv run python scripts/scan_source_secrets.py
uv export --locked --no-emit-project --no-hashes --format requirements-txt --output-file .local/audit-requirements.txt
uv run pip-audit --strict --no-deps --disable-pip --requirement .local/audit-requirements.txt
git diff --check
```

The tool installer creates `.local/ci-tools/`; the final audit export also uses ignored `.local/`. On Linux, omit `.exe` from tool names. The local results were obtained on Windows; the hosted Ubuntu jobs remain a separate verification gate.

## Azure preview and production acceptance

The suite in `tests/test_azure.py` is opt-in. Close other editing sessions first so no operator changes the table fingerprints while it runs. It requires the existing protected `.env.preview`, `.env.production` and `.local/azure/application-accounts.json` files. It never provisions resources, seeds permanent data, runs migrations, resets credentials or drops databases.

```powershell
$env:EMS_AZURE_TESTS = '1'
try {
    uv run --locked python -m unittest discover -s tests -p test_azure.py -v
    if ($LASTEXITCODE -ne 0) { throw 'Azure acceptance failed; inspect the test output.' }
} finally {
    Remove-Item Env:EMS_AZURE_TESTS -ErrorAction SilentlyContinue
}
```

For each environment, the suite verifies the exact database name, contained runtime username, schema version, lack of database ownership and lack of table-creation permission before writing. Tests generate unique IDs and use one explicit outer transaction per test. Service sessions use savepoints for normal operations; intentional SQL constraint failures use rollback-only participation because `XACT_ABORT` can abort the whole SQL Server transaction. Every path closes connections and rolls back the outer transaction. Complete contents of all six application tables are hashed before testing and compared after each test and at suite cleanup; records and stored password hashes are not printed.

The nine tests per environment cover:

1. Application administrator/viewer authentication, account creation, first-admin refusal, all viewer read/write restrictions and failed-login session clearing.
2. Console login, record lists, updates, review creation, deletion cancellation/confirmation, logout and viewer login.
3. Duplicate employee rejection by the database.
4. Invalid employee/position department assignment rejection by the database.
5. Negative compensation rejection by the database.
6. Invalid review rating rejection by the database.
7. ORM employee CRUD, exact computed compensation, phone leading zero, injection text stored as data, reporting without reviews and employee/review removal.
8. Interrupted-transaction recovery and invalid IDs, email, phone, dates and money.
9. Actual short-command configuration selection, live schema check, console startup and shutdown.

## Recorded results

| Executed check | Result |
| --- | --- |
| Local unit/ORM/console/operator-tool suite | 52 passed; 18 Azure acceptance tests and 2 dedicated SQL Server tests skipped in this run |
| Branch-aware application coverage | 92%, above the 85% gate |
| Live Azure preview acceptance | 9 passed |
| Live Azure production acceptance | 9 passed |
| Fresh-schema integration contract on a temporary Azure database | Passed |
| Original-schema migration/rollback/password-upgrade contract on a temporary Azure database | Passed after repairing the phone-constraint compilation error |
| Database preservation | All six application table fingerprints unchanged after every live test |
| Ruff lint/format | Passed |
| Actionlint | Passed |
| Repository validation | Passed, including all ten historical file hashes |
| Gitleaks history/source scans | No leaks found; detector/redaction self-test passed |
| Locked dependency vulnerability audit | No known vulnerabilities found |

The live run completed 18 tests in approximately 168 seconds. Its transcript is stored locally under ignored `.local/azure/acceptance-test.log`. The unit and coverage results are separate from this live run; skipped tests are not counted as passes.

The initial cold Azure connections returned resume error 40613. Connection opening now retries only that error with bounded 5, 10 and 15-second waits. Regression tests verify retry exhaustion, no retries for authentication failures and sanitized diagnostics. Reads of different configuration files no longer mutate process environment variables or contaminate subsequent environment selection.

Hosted GitHub Actions, CodeQL execution and Dependabot update PRs have not run for these unpublished changes. The native SQL Server 2022 hosted job is configured and linted; actual platform execution remains a separate hosted check. Both integration contracts have now executed against temporary Azure SQL databases. Existing production/preview schemas were not migrated or reset. Billing statements, recovery drills and application hosting are outside these checks.

## Run schema and migration integration without local database software

The same two contracts in `tests/test_sql_server.py` can run through Azure CLI using the existing operator identity:

```powershell
uv run --locked python scripts/test_azure_migrations.py
```

This is an explicit provisioning command. It reads the ignored Azure export, creates at most two UUID-named free databases per run and runs tests only after confirming `useFreeLimit=true`, `AutoPause` and an empty schema. It uses in-memory Entra tokens, then deletes only databases with the exact expected resource ID and the current run's ownership tag. It verifies resource absence after deletion. Local records are under `.local/azure/integration-run.json` and integration log files. A missing test connection in the ordinary unit suite remains an intentional skip; this separate command executes the cloud contracts.

Use `--test fresh` or `--test migration` for a targeted rerun. These commands also create and remove temporary free databases. If a run is interrupted, inspect its local ownership record and matching Azure resource tags before resuming cleanup. Never substitute production or preview names for generated test names, and keep `EMS_TEST_SERVER_CONNECTION` reserved for a dedicated native test server.

The fresh-schema contract passed on its first run. The migration contract exposed SQL Server compiling the phone constraint while the legacy column still had type `BIGINT`. The migration now compiles that fixed text constraint after changing the column to `VARCHAR`. Strengthened checks verify the intended department-mismatch preflight error, rollback after an actual name-constraint failure, successful conversion, repeated migration, preserved records and legacy-password upgrade. The repaired contract passed on its targeted rerun. All three temporary databases used across these runs were deleted and their absence verified.

Additional offline safety tests verify refusal to delete production names, mismatched resource IDs or another run's databases; deletion absence checks; correct separation of network failures from authentication denials; and construction of the certificate-hostname negative test.

See the [database security verification](DATABASE_SECURITY_VERIFICATION.md) for the live security findings and remaining hardening gaps.

On 2026-11-01 (Asia/Karachi), the local suite passed 52 tests with 92% branch-aware application coverage. After installing the supplemental journal, all 18 Azure acceptance tests passed again in 148 seconds with business fingerprints unchanged. Additional live checks verified committed/rolled-back journal behavior, account promotion/demotion metadata and denied runtime journal tampering in each database. The on-demand review completed and flagged authorized installation DDL for review. See [free-only hardening](FREE_SECURITY_HARDENING.md) for commands and limitations; managed protection remains deferred, and no always-on PC or paid resource was introduced.
