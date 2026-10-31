# Employee Management System

[![Quality and tests](https://github.com/asteroidcrib729/employee-management-system/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/asteroidcrib729/employee-management-system/actions/workflows/ci.yml)
[![Security](https://github.com/asteroidcrib729/employee-management-system/actions/workflows/security.yml/badge.svg?branch=main)](https://github.com/asteroidcrib729/employee-management-system/actions/workflows/security.yml)

I built this project as a Python and SQL Server database coursework application. This version keeps the console interface and original employee-management scope while adding validated input, controlled account creation, transaction handling, migration support, and regression tests.

I preserve the original reports, diagrams, archive, and source under [development-plans/legacy](development-plans/legacy/README.md). Those documents describe the coursework version. The current implementation is documented here and in [the design notes](development-plans/design.md).

For two free Azure SQL databases, follow [the detailed production and preview setup guide](development-plans/AZURE_SQL_SETUP_GUIDE.md). Azure's free limits and availability restrictions are explained there.

The configured workstation environment, live Azure checks and commands for starting production or preview are recorded in [the current Azure environment notes](development-plans/AZURE_ENVIRONMENT.md). Credentials stay in ignored local files.

## What it does

- Administrators add/list departments and positions, manage employee records, add/list performance reviews, view a combined report, and create administrator or viewer accounts.
- Viewers can list departments and position descriptions. They cannot access employee details, salaries, reviews, salary ranges, or management operations.
- There is no public signup. A trusted database operator provisions the first administrator; subsequent accounts require an administrator.
- Passwords are hidden while typing and stored with a random salt using PBKDF2-HMAC-SHA256 at 600,000 iterations. Verified legacy SHA-256 hashes are upgraded on login.
- Dates, IDs, lengths, decimal amounts, phone numbers, salary ranges, and ratings are validated. SQL constraints also enforce valid assignments and compensation values.
- Application reads and writes use SQLAlchemy ORM models, bound parameters and short sessions. A failed operation rolls back its transaction. Missing employees produce a not-found result. Connections are released after each operation.

This is a console administration application. It does not implement payroll processing, payroll history, employee self-service, dashboards, or analytics.

## Requirements

- Exactly Python 3.14.7, pinned in `.python-version`, package metadata and CI, and [uv](https://docs.astral.sh/uv/).
- An accessible SQL Server 2016 SP1 or newer database, or Azure SQL Database.
- [Microsoft ODBC Driver 18 for SQL Server](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server).
- SQL Server Management Studio or another trusted SQL administration tool for database creation, backups, and migration review.

## Install and configure

Run from the repository root in PowerShell:

```powershell
uv python install 3.14.7
uv sync --locked
```

The configured workstation already has `.env.preview` and `.env.production`. On a new workstation, copy `.env.example` to those filenames and supply each Azure database's separate runtime credentials. Keep existing files intact. Real configuration files are ignored by Git; never commit credentials or database backups.

Launch from the repository root:

```powershell
uv run ems            # Preview (default)
uv run ems production # Production
```

With the virtual environment activated, the commands shorten to `ems` and `ems production`. `ems preview` is also accepted. `--env-file` remains available for a custom operator configuration and cannot be combined with an environment name. Missing configuration files fail closed. The obsolete localhost `.env` has been removed.

Existing process environment variables take precedence without being modified by loading a file; remove a stale `EMS_CONNECTION_STRING` override before switching environments. Both Azure runtime files require encryption and certificate validation. The program refuses system databases such as `master`. `--help` works without connecting. Initial connection attempts retry Azure resume error 40613 at most three times, waiting 5, 10 and 15 seconds; application writes are never replayed automatically.

Runtime dependencies remain SQLAlchemy 2.1.6 and pyodbc 5.3.0. Development checks use Ruff 0.17.3, coverage 7.17.0, pip-audit 2.10.1 and PyYAML 6.0.3; setuptools 84.2.1 builds the package. Exact versions and hashes are recorded in `uv.lock`. Upgrades must be compatible with Python 3.14.7 and pass the same checks.

## New database

The configured Azure databases are initialized already. For a new empty database, follow the [Azure setup guide](development-plans/AZURE_SQL_SETUP_GUIDE.md). Use a separate operator configuration with database-owner permissions for initialization:

```powershell
uv run ems --env-file .env.preview.admin --init-db
uv run ems --env-file .env.preview.admin --create-admin
uv run ems
```

The first administrator command prompts for a new username and a confirmed 12–128-character password. Use an interactive terminal; password entry refuses an unsafe echo fallback. The command refuses to create another bootstrap administrator once one exists. Administrators can create more accounts from the signed-in menu.

To insert optional fictional sample records:

```powershell
uv run ems --env-file .env.preview.admin --seed-demo
```

The seed inserts missing IDs only. It does not overwrite existing records, change employee names, or create accounts. Twenty records per business table are supplied. Repeating schema initialization or seeding is safe for the current version. Existing records that conflict with sample relationships cause a rollback instead of being overwritten.

## Existing coursework database

1. Back up the database using your SQL Server administration tool, verify the backup, and stop application sessions.
2. Run [000_preflight_legacy.sql](src/ems/sql/000_preflight_legacy.sql) against that database. Review the returned records.
3. Reconcile inconsistencies explicitly. For example, the original sample `EMP000005` belongs to `DEPT000004`, while its position belongs to `DEPT000005`. Decide which assignment is correct before updating anything. The migration never chooses for you.
4. Point a separate operator file at the existing database and run `uv run ems --env-file .env.migration.admin --migrate`.
5. Run `uv run ems --env-file .env.migration.admin --create-admin` using an unused username, then configure the intended runtime file before starting the application.

The migration is transactional. Invalid existing records stop it, and schema changes roll back. Employee records, reviews, usernames, and password hashes are preserved. Existing accounts become viewers. Password hashes upgrade after a successful login; historical nine-character passwords remain usable for migration. New passwords must meet the current length rule.

Phone numbers become text, and money becomes `DECIMAL(12,2)`. Migration refuses values requiring rounding or exceeding supported limits. Leading zeroes already lost by the original numeric phone field cannot be reconstructed; verify those values against the original contact records. Changes outside the original coursework schema require separate migration review.

The preflight file only reads data. There is no active database-drop/reset command. The original destructive reset SQL is preserved inside the historical source ZIP and must not be used for setup.

## Compensation and review rules

`BaseSalary` and `Bonus` are **monthly recurring amounts**. `AnnualCompensation = (BaseSalary + Bonus) * 12`. A one-off bonus must not be entered as a monthly recurring bonus. Position salary ranges describe monthly base pay; an employee's actual pay is not automatically forced into that range. Amounts accept up to two decimal places and must be between zero and 9,999,999,999.99. Ratings use the original 0–9 scale.

Phone numbers preserve an optional leading `+` and 7–15 digits, including leading zeroes. Empty optional phone, email, description, and comment fields become SQL `NULL`.

## Database permissions

Keep the connection configuration accessible only to trusted operators. Bootstrap, initialization, migration, and seeding are operator commands, not options inside a viewer session. Application roles protect service operations; someone with direct database access can bypass application roles. This console application does not isolate users who share the same unrestricted SQL credentials or can modify its source.

Use a separate database-owner account for setup and migration. For ordinary application use, grant only the required `SELECT`, `INSERT`, `UPDATE`, and `DELETE` permissions on the five application tables, `SELECT` on the report view, and `SELECT` on `EMS_SchemaVersion`; omit DDL and server administration permissions. SQL authentication secrets must be protected by the operating system. Five failed login attempts close the console session; this is not a persistent account-lockout system.

## Verification

```powershell
uv run python -m unittest discover -s tests -v
uv run coverage run -m unittest discover -s tests -v
uv run coverage report
uv run ruff check .
uv run ruff format --check .
uv run python scripts/validate_repository.py
```

Tests run real SQLAlchemy sessions against isolated SQLite fixtures for CRUD, constraint failures, rollback, authorization, password migration, report joins and SQL-injection regressions. SQLite is used only by tests; SQL Server remains the application backend. SQL Server lock hints are also compiled with its dialect. These checks do not establish live SQL Server compatibility.

The opt-in SQL Server tests require `EMS_TEST_SERVER_CONNECTION` pointing at a **dedicated test server** with database-creation permission. They create unique `ems_test_<uuid>` databases and clean up only those generated databases. They cover fresh initialization, repeated seeding, constraints, CRUD, permissions, legacy migration rollback, and password upgrades. Do not give this test account access to production servers.

Docker is unnecessary. CI uses a disposable instance of SQL Server Express LocalDB already installed on GitHub's Windows runner. The same two integration contracts also have an explicit [Azure test runner](scripts/test_azure_migrations.py) that creates, verifies and deletes its own temporary free databases. Both contracts have passed through that runner. See [the testing guide](development-plans/CI_AND_TESTING.md#run-schema-and-migration-integration-without-local-database-software) before executing this provisioning command.

The [CI and testing guide](development-plans/CI_AND_TESTING.md) describes the Windows/Linux unit matrix, 85% coverage gate, linting, Actionlint, package/configuration validation, disposable SQL Server integration, CodeQL, Gitleaks, dependency audits and Dependabot. These workflows do not receive Azure credentials. The badges above link to current hosted results; recorded verification identifies the tested revision and run links.

The separate opt-in Azure suite exercises preview and production inside outer rollback transactions and verifies complete table fingerprints after every test. Run it only while no other operator is editing those databases. Its repeatable command and safeguards are documented in the testing guide.

[Live database security verification](development-plans/DATABASE_SECURITY_VERIFICATION.md) records the encryption, authentication, permission and isolation checks, together with remaining auditing and threat-protection gaps.

The [free-only hardening guide](development-plans/FREE_SECURITY_HARDENING.md) documents the installed committed-change journal, runtime tampering denials and on-demand security review. Run `uv run --locked python scripts/security_review.py` when online. Paid Defender protection and native SQL auditing remain deferred; the supplemental controls do not establish full readiness for real employee data.

See [the local verification record](development-plans/verification.md) for the checks actually completed and their limits.

## Layout

```text
src/ems/                       Console, ORM models, validation, authentication and services
src/ems/sql/                   Preflight, schema, migration, sample data and change journal
tests/                         Console/ORM tests and opt-in SQL Server integration tests
development-plans/            Design notes, verification and Azure setup guide
development-plans/legacy/     Preserved coursework artifacts and original file hashes
```

Password parameters follow [OWASP's password storage guidance](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html). Composite relationship constraints follow [Microsoft's SQL Server constraint documentation](https://learn.microsoft.com/en-us/sql/relational-databases/tables/primary-and-foreign-key-constraints).

## License

I release this project under the [Apache License 2.0](LICENSE). [NOTICE](NOTICE) preserves my author and original repository attribution. See [licensing and attribution](development-plans/LICENSING.md) for redistribution details and the boundaries covering preserved coursework, dependencies and private data.
