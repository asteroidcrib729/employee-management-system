# Current verification record

Local snapshot: **2026-11-01**, Asia/Karachi.

## Layout, interpreter and dependencies

- Documentation is under `development-plans/`; application code is under `src/ems/`.
- Python is pinned to **3.14.7** in `.python-version`, `requires-python` and the uv-based CI jobs.
- Apache-2.0 is declared in package metadata; the canonical LICENSE and project NOTICE are included byte-for-byte in wheel/source artifacts. See [licensing](LICENSING.md).
- Latest compatible stable direct releases were checked through PyPI: SQLAlchemy **2.1.6**, pyodbc **5.3.0**, Ruff **0.17.3**, and setuptools **84.2.1**. The refreshed lock includes typing-extensions **4.16.0**.
- Dependency installation succeeded with the pinned interpreter. The obsolete localhost `.env` was subsequently removed; `.env.preview` and `.env.production` remain private.

## Verification scope

| Completed local check | Result |
| --- | --- |
| Interpreter | Python 3.14.7 |
| Local test suite | 52 passed, 18 opt-in Azure and 2 dedicated SQL Server tests skipped |
| Branch-aware coverage | 92%; required minimum 85% |
| Separate live Azure acceptance | 18 passed: 9 preview and 9 production |
| Separate temporary Azure integration | Fresh schema and repaired legacy migration contracts both passed; owned temporary databases deleted |
| Live database security verification | Core controls and six journal triggers passed in both environments; native auditing and managed threat protection deferred |
| Committed change journal | Both environments: durable events verified, rollback events discarded, promotion/demotion logged, runtime tampering denied; business fingerprints unchanged |
| On-demand security review | Live review completed without inconclusive sources; installation DDL flagged for review as expected; no daemon or paid destination |
| Ruff lint and formatting | Passed |
| Upgraded dependency lock | Passed `uv lock --check --offline` |
| Wheel and source distribution | Built successfully; metadata pins Python 3.14.7 |
| Packaged runtime | Imported from the wheel outside the checkout working directory; help and all five SQL resources verified |
| Packaging exclusions | No local `.env`, environment, cache or Git files included |
| Source layout and guide | `src/ems`, interpreter pin and Azure guide verified in distribution contents |
| Original artifacts | All ten historical SHA-256 hashes still match |
| Markdown links and anchors | All local targets resolve |
| SQL and example syntax | Active scripts, embedded batches, guide SQL and guide PowerShell passed syntax parsing |
| Repository whitespace | `git diff --check` passed |

The suite now runs real SQLAlchemy sessions against isolated SQLite databases. It covers employee CRUD, decimal compensation, phone preservation, computed compensation, duplicate/FK rollback, atomic review deletion, interrupted transactions, authentication and legacy password upgrades, permissions, report joins, SQL injection payloads and independent environment data.

Additional tests cover validation, hidden passwords, complete console journeys, configuration precedence and isolation, short launch commands, missing configuration files, resume-only connection retries, administrative cursor/connection cleanup, setup-script allowlisting and SQL Server lock-hint compilation. The engine configuration is checked for `NullPool`, disabled pyodbc pooling and hidden SQL parameters.

SQLite fixtures do not establish live SQL Server or Azure SQL compatibility. The two opt-in SQL Server integration tests remain gated on `EMS_TEST_SERVER_CONNECTION`. They use generated disposable databases and now exercise the ORM service against SQL Server, including the existing migrations.

## Checks to reproduce

```powershell
uv sync --locked
uv run --locked python --version
uv run --locked python -m unittest discover -s tests -v
uv run --locked ruff check .
uv run --locked ruff format --check .
uv build
git diff --check
```

Wheel/source archive inspection confirmed that the `src` package imports as `ems`, all five SQL resources and the Azure guide are present in their appropriate artifacts, and no local environment or cache files are included. The wheel smoke check used the locked environment's dependencies while importing application code directly from the built wheel with isolated Python startup. Original coursework hashes are recorded under `legacy/original-hashes.json` and remain unchanged.

The Azure guide was checked against current Microsoft free-tier, CLI, firewall, account, permissions, cost-budget and serverless documentation. Its generic names are examples; the provisioned environment is recorded in [the current Azure environment notes](AZURE_ENVIRONMENT.md).

## Live Azure SQL verification

After Azure CLI installation and sign-in on 2026-10-31, live management and SQL access were verified. The existing `sql-emp-db` database was retained, and `sql-emp-db-preview` was created on the existing server. Both databases were confirmed empty before initializing schema version 1. Preview received 20 fictional sample employees; production has zero business records. Each environment has one application administrator and a separate contained runtime SQL user. Secret files are ignored and protected by Windows file permissions.

Live ORM smoke checks passed against preview for employee CRUD, review removal, computed decimal compensation, phone preservation, injection text, report outer joins, viewer permissions, failed login handling and temporary-record cleanup. Both runtime administrator logins passed. Cross-environment SQL authentication was rejected in both directions. Runtime users are not database owners and cannot create tables.

Both resources report `useFreeLimit=true`, `freeLimitExhaustionBehavior=AutoPause`, serverless `GP_S_Gen5`, 0.5-2 vCores, a 32 GiB data limit, local backups and API `autoPauseDelay=60`. Microsoft's [free-tier documentation](https://learn.microsoft.com/en-us/azure/azure-sql/database/free-tier#considerations-and-limitations) specifies a fixed 15-minute inactivity pause; the API property does not establish the effective free-tier delay, and a timed pause was not tested. The existing single-client-IP firewall rule was retained. The signed Microsoft ODBC Driver 18 installer completed successfully, and Python enumerates the driver.

The expanded Azure acceptance suite subsequently passed all nine tests in both preview and production (18 total), including real database constraint failures, interrupted transactions, viewer restrictions and console startup. It used outer rollback transactions and verified that full-table fingerprints of all six tables remained unchanged after every test. Production retains zero business records; preview retains its 20 fictional records per business table.

The [CI and testing guide](CI_AND_TESTING.md) records repeatable commands and the expanded checks: immutable action pins, Actionlint, repository/package validation, coverage, Gitleaks with a detector/redaction self-test, vulnerability auditing, CodeQL, dependency review and Dependabot. Local Gitleaks scans found no leaks, and pip-audit found no known vulnerabilities in the locked runtime/development dependencies.

The default unit run intentionally skips the opt-in database suites. The two integration contracts were separately executed against temporary free Azure databases, including original-schema migration, rollback, record preservation and password upgrades. A migration phone-constraint compilation error was reproduced, repaired and verified. All temporary databases were deleted. The hosted CI job now uses a preinstalled LocalDB instance on Windows and has executed both contracts successfully; local Docker is unnecessary.

Hosted quality and security workflows passed at `325e7ba369810c23bd12fbe33ea2febbe6ab3cc9`; all four initial Dependabot update jobs passed. See [hosted verification](CI_AND_TESTING.md#hosted-verification) for immutable run links, executed checks, the PR-only dependency-review boundary, and the legacy-hash CodeQL triage. README badges show current branch status. See [the security verification](DATABASE_SECURITY_VERIFICATION.md) for database controls and logging gaps. Subscription billing, recovery drills and an application-host deployment remain outside this verification.
