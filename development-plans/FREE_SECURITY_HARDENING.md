# Free-only security controls and deferred protection

Updated 2026-11-01 (Asia/Karachi). This project uses on-demand operator review. This PC does not need to stay online. No paid plan, trial, audit destination, scheduled collector or new cloud resource is provisioned by these scripts.

**These controls harden the current trusted-operator console application. They do not establish complete protection for real employee data.** Native SQL access auditing, managed threat detection and an independent protected archive remain deferred under the free-only deployment. The operational prerequisites below also require resolution before introducing real employee data.

## Implemented controls and boundaries

| Capability | Implementation | Boundary |
| --- | --- | --- |
| Encryption and restricted access | TDE, validated TLS, one-IP firewall, separate contained users, limited object grants | Existing [live verification](DATABASE_SECURITY_VERIFICATION.md); no external penetration test |
| Committed business changes | Five database DML triggers journal changes to departments, positions, employees, reviews and accounts | Captures application and direct SQL writes; excludes reads, failed operations and rolled-back changes |
| Schema/security changes | Database DDL trigger records event type and object name | SQL text excluded; owners can disable or replace the mechanism |
| Runtime journal protection | Explicit SELECT/INSERT/UPDATE/DELETE DENY on journal and feature table | Owned triggers append events; runtime cannot directly read, forge or delete them |
| Security triage | On-demand [security_review.py](../scripts/security_review.py) | No continuous detection, external notifications or automatic remediation |
| Connection diagnostics | Existing `master.sys.event_log` failure summaries | Delayed/incomplete troubleshooting data, not an application login audit |
| Cost protection | Existing free databases, exhaustion behavior `AutoPause` | Checks and journal storage consume existing allowance; exhaustion can stop availability |

[004_change_journal.sql](../src/ems/sql/004_change_journal.sql) stores UTC time, a per-statement correlation ID, database actor, object/event type, affected record ID and account-role metadata. An admin role before **or** after an account change is marked, so both promotion and demotion receive review. It excludes employee names, contact details, pay values, review comments, password hashes and SQL text. Record IDs and usernames remain confidential metadata. `ClaimedAppActor` is optional, untrusted session metadata; the current console leaves it unset. `DatabaseActor` identifies the shared SQL account, not an independently verified human console user.

Each row and its journal entry commit or roll back together. Journal failure stops the originating change. All five ORM mappings disable implicit RETURNING to support SQL Server triggers, following [SQLAlchemy's guidance](https://docs.sqlalchemy.org/en/21/dialects/mssql.html#triggers). Application data operations continue using the ORM; installation and inspection use fixed administrative SQL.

## Install and verify

The current preview and production installations passed the checks below. These steps also apply when rebuilding an environment.

1. Complete the [Azure SQL setup guide](AZURE_SQL_SETUP_GUIDE.md), including version-1 schema, `ems_app_runtime` role, contained runtime user and protected runtime file. Use separate operator credentials for administration.
2. Sign in to Azure CLI as the authorized operator. Scripts read ignored `.local/template/parameters.json` and hold the Entra token in memory. Never paste tokens or connection files into chat, issues or CI.
3. Close other application sessions so fingerprint comparisons remain meaningful.
4. Install and verify preview first:

   ```powershell
   uv run --locked python scripts/install_change_journal.py preview
   ```

   The command refuses a target without free-limit AutoPause protection. It installs transactionally, checks all six triggers, exercises runtime CRUD with rollback, verifies discarded journal events, checks account promotion/demotion metadata without keeping the account, and probes direct journal read/insert/update/delete denials. A synthetic department insert/delete pair commits in one transaction: no business row remains, while two durable journal events prove commit behavior.

5. After preview passes, apply the same checks to production:

   ```powershell
   uv run --locked python scripts/install_change_journal.py production
   ```

   No employee is permanently inserted, updated or removed. Both commands compare complete fingerprints of all six existing application tables. Reports are written under ignored `.local/azure/change-journal-<environment>.json`. Repeating installation updates reviewed trigger definitions and intentionally adds installation metadata and two proof events.

6. Run baseline verification and the live acceptance suite:

   ```powershell
   uv run --locked python scripts/verify_azure_security.py
   $env:EMS_AZURE_TESTS = '1'
   uv run --locked python -m unittest discover -s tests -p test_azure.py -v
   Remove-Item Env:EMS_AZURE_TESTS
   ```

   Docker is unnecessary. See the [testing guide](CI_AND_TESTING.md) for credentials and rollback safeguards. Baseline success means the enumerated controls passed; its report explicitly declines full production security certification.

## Review when this PC is online

Run before/after sensitive maintenance, after an unexpected application error, and when returning after an absence:

```powershell
uv run --locked python scripts/security_review.py
```

The default window is 24 hours. A bounded seven-day review is also available:

```powershell
uv run --locked python scripts/security_review.py --hours 168
```

The command reads existing data and replaces ignored `.local/azure/security-review.json`. It creates no resource and sends nothing to another service. It reports journal configuration drift, missing free-limit protection, storage at 80% or more, administrator account changes, schema/security changes, at least five employee deletions in one UTC 15-minute bucket, and at least five SQL login failures in one diagnostic aggregation interval. Unattributed failures contribute to both environments' triage and are separately counted at server level; do not add those environment counts as independent incidents.

Signals require investigation; they are not proof of an attack. Authorized installation, account maintenance and negative security tests can produce signals. Console authentication failures are not captured by SQL connection-failure diagnostics.

| Exit code | Meaning | Response |
| --- | --- | --- |
| 0 | No configured signal found in this limited window | Does not establish absence of attacks |
| 2 | Signals need operator review | Compare with authorized maintenance; investigate unexpected changes |
| 3 | Review incomplete or unavailable | Resolve access/connectivity or narrow the window; never interpret missing data as clean |

Queries use bounded windows and limits of 1,000 connection diagnostic rows / journal groups per database. Reaching a limit is inconclusive. No background loop, Windows scheduled task, always-on service or automated message delivery is installed.

Microsoft documents five-minute diagnostic aggregation, potentially up to 24 hours of delay, and retention of at most 30 days, sometimes less. Some failures are omitted. See [sys.event_log](https://learn.microsoft.com/sql/relational-databases/system-catalog-views/sys-event-log-azure-sql-database). Long offline intervals can lose diagnostic history. The database journal continues recording committed changes while this PC is off, subject to database availability/storage limits. No operator alert is evaluated or delivered during that absence.

For unexpected signals, preserve the sanitized report in protected local storage, pause real-data entry, and rerun baseline verification. Inspect affected metadata privately using the operator identity. Reconcile permission/account changes with approved maintenance. Suspected compromise requires access isolation and reviewed credential rotation; do not erase journal history to make reports clean. Keep credentials, employee data and raw SQL diagnostics out of public issues.

## Deferred under the free-only requirement

1. **Defender for SQL / advanced threat protection.** This is a paid plan; its trial is not used. Managed attack detection and alerts remain disabled. See [Microsoft Defender for SQL](https://learn.microsoft.com/en-us/azure/azure-sql/database/azure-defender-for-sql) and [Defender pricing](https://azure.microsoft.com/en-us/pricing/details/defender-for-cloud/).
2. **Native SQL activity audit with a protected external destination.** [Azure SQL auditing](https://learn.microsoft.com/en-us/azure/azure-sql/database/auditing-overview) supports Storage, Log Analytics and Event Hubs. No destination has been established as permanently free for this workload; none was created or enabled. SELECTs and denied/rolled-back SQL activity therefore have no complete SQL audit trail here.
3. **Independent continuous monitoring and tamper-resistant retention.** Owners control the same-database journal. It cannot prove integrity after owner-level compromise. No independently hosted collector or guaranteed free protected archive has been established; this PC is intentionally not an always-on collector.

The journal and rules supplement existing defenses. They do not replace native SQL Audit or Defender, guarantee compliance, or guarantee availability. Free-limit protection is a resource setting, not verification of the subscription's whole bill.

## Prerequisites before real employee information

These are distinct from deferred paid services. Several involve free controls or operational decisions; they must not be presented as completed because scripts pass.

- Maintain the **trusted-operator** boundary. A holder of shared runtime SQL credentials can bypass console viewer roles and change account records directly. Do not distribute those credentials to employee end users. An untrusted multiuser deployment needs separately reviewed authentication and authorization.
- Verify operator MFA/recovery, review Owner access and protect administrator credentials. Tenant security defaults/MFA and the unseen SQL administrator password were not changed or certified by this project-scoped work.
- Decide data purpose, minimum fields, retention/deletion policy, authorized operators and incident ownership before import. Keep real data and production credentials out of preview/tests/source control. Verify workstation protection separately; restricted file ACLs do not establish disk encryption or endpoint integrity.
- Decide retention/export requirements for confidential journal identifiers. **No automatic pruning is implemented.** The journal consumes existing storage and can eventually block writes. Review capacity; future deletion must be an explicit operator decision consistent with retention requirements.
- Complete a recovery exercise before relying on employee operations. Encryption and platform backup settings do not prove successful restore. No restore drill or paid restore target was created in this work.
- Accept the explicit monitoring gaps, quota outages and lack of independent audit integrity, or defer real employee data until requirements can be met.

## Evidence

The local suite covers rule thresholds, drift/cost/capacity signals, omission of sensitive fields and unavailable-log handling. Each environment's live installation check proves committed event persistence, discarded rolled-back events, promotion/demotion metadata, denied runtime tampering and unchanged business fingerprints. The separate live 18-test acceptance suite exercises application functionality with triggers enabled. Sanitized reports remain ignored under `.local/azure`. Hosted quality/security workflows and the disposable LocalDB integration tests have passed; see [hosted verification](CI_AND_TESTING.md#hosted-verification). Those hosted checks receive no Azure credentials and do not establish additional live-database protection.
