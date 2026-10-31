# Database security verification

Verified **2026-10-31 UTC** against the live `sql-emp-db` production database and `sql-emp-db-preview` preview database. The repeatable operator check is [verify_azure_security.py](../scripts/verify_azure_security.py). Its final report returned `core_controls_passed=true`.

**The tested access and encryption controls passed. Native SQL auditing and managed advanced threat protection remain deferred under the free-only requirement. A supplemental committed-change journal and on-demand security review were added on 2026-11-01. This remains a trusted-operator application with explicit limits before real employee information is introduced.** See the [free-only hardening guide](FREE_SECURITY_HARDENING.md) for commands, evidence and deferred capabilities.

## Live results

| Control | Production | Preview |
| --- | --- | --- |
| Transparent data encryption policy | Enabled | Enabled |
| Actual database encryption state | 3 - encrypted | 3 - encrypted |
| Encrypted SQL transport observed | TRUE | TRUE |
| Minimum server TLS | 1.2 | 1.2 |
| Runtime client encryption / certificate validation | Required / enabled | Required / enabled |
| Incorrect certificate hostname | Rejected | Rejected |
| Incorrect SQL password | Rejected | Rejected |
| Credential used against the other database | Rejected | Rejected |
| Expected contained SQL user | `ems_production_app` only | `ems_preview_app` only |
| Runtime role membership | `ems_app_runtime` only | `ems_app_runtime` only |
| Database-level runtime grant | CONNECT only | CONNECT only |
| Required table/view grants | Exactly expected | Exactly expected |
| Public grants on business objects | None | None |
| Runtime CREATE TABLE attempt | Denied | Denied |
| Runtime attempt to join db_owner | Denied | Denied |
| Runtime attempt to impersonate dbo | Denied | Denied |
| CHECK and foreign-key constraints | Enabled and trusted | Enabled and trusted |
| Application password hashes | Current salted PBKDF2 policy | Current salted PBKDF2 policy |
| Additional database firewall rules | None | None |
| Application data after verification | Full-table fingerprints unchanged | Full-table fingerprints unchanged |
| Database auditing | Disabled | Disabled |

The shared server has one single-client-IP firewall rule, no all-Azure-services rule, and no private endpoint. Public network access is enabled and restricted by that rule. Its Entra administrator is configured, and inherited Azure RBAC enumeration found one Owner assignment. The review did not retrieve or publish directory principal names or tokens.

Each runtime role has 22 object grants: SELECT/INSERT/UPDATE/DELETE on the five application/account tables, SELECT on the schema-version table, and SELECT on the reporting view. The journal extension adds eight explicit object DENYs covering SELECT/INSERT/UPDATE/DELETE on its journal and feature tables. There are no extra direct privileged grants. Effective permission checks returned zero for CONTROL, ALTER ANY ROLE, ALTER ANY USER, CREATE TABLE, ALTER ANY SCHEMA and impersonation of dbo. Live denial probes corroborated schema-change, role-escalation and impersonation restrictions.

The account-table review checked hash format, random-salt representation and a PBKDF2-SHA256 work factor of at least 600,000 iterations without printing hashes. Application administrator/viewer enforcement was separately exercised by the [18-test Azure acceptance suite](CI_AND_TESTING.md#azure-preview-and-production-acceptance).

## What the negative tests establish

The connection tests changed only the selected database, password or certificate expectation. Authentication denials were identified from SQL error codes. Timeouts and unrelated network failures are classified as inconclusive, never counted as successful security checks. Offline tests cover this distinction.

For certificate verification, the test connects to the real Azure endpoint IP with a deliberately invalid expected hostname. This matters because Microsoft's ODBC driver can accept a certificate matching either the server hostname or `HostNameInCertificate`; retaining the valid server hostname would make a negative test misleading. The final test removes that valid hostname and confirms a certificate-related SQLSTATE 08001 rejection. The regular runtime connection remains encrypted and uses the normal Azure hostname with certificate trust bypass disabled. See Microsoft's [ODBC connection keyword documentation](https://learn.microsoft.com/en-us/sql/connect/odbc/linux-mac/connection-string-keywords-and-data-source-names-dsns).

Permission probes use generated object names and explicit transactions. Every path rolls back. No application records, account passwords, roles, firewall settings or encryption policies were permanently changed. Full contents of all six application tables were fingerprinted before and after the probes. The report records booleans and security metadata rather than employee records, passwords or stored hashes.

## Remaining gaps and operating boundaries

1. **Native SQL auditing is deferred at server and database levels.** No guaranteed free protected destination has been established. The new database change journal covers committed changes, with runtime tampering denied; it excludes reads, denied attempts and rollbacks, and cannot resist database-owner compromise. Azure management activity logs do not replace SQL access auditing. [Azure SQL auditing](https://learn.microsoft.com/en-us/azure/azure-sql/database/auditing-overview)
2. **Managed advanced threat protection is deferred.** No paid plan or trial was enabled. On-demand checks report limited signals while invoked; the PC does not need to remain online and no continuous alerting is provided. See the [free-only guide](FREE_SECURITY_HARDENING.md).
3. **The endpoint is public with a single-IP allowlist.** Keep the rule narrow when the operator's public IP changes. Private connectivity would be a separate architecture and cost decision. This verification inspected effective firewall configuration; it did not conduct an external penetration test from an untrusted network.
4. **Runtime credentials belong to trusted operators.** A holder of the SQL runtime password can directly read/write the tables granted to that account, including application account records. Console viewer roles govern the console service and do not isolate someone who holds the shared SQL credentials. Protect the ignored connection files and local account file using the existing operator/SYSTEM-only Windows permissions.
5. **Cloud identity controls have a wider scope.** Entra administrator presence and inherited RBAC roles were checked. Tenant MFA/Conditional Access policy, the unseen server administrator password, compromise detection, recovery drills and regulatory compliance were not certified by this check.

Microsoft's [Azure SQL security guidance](https://learn.microsoft.com/en-us/azure/azure-sql/database/secure-database) describes these controls as complementary layers. Passing the checks above is evidence about the inspected configuration and tested access paths, not a guarantee against every attack.

## Repeat the verification

Use the existing signed-in Azure CLI operator identity, ignored `.local/template/parameters.json`, and protected runtime files. Run while no other operator is editing records:

```powershell
uv run --locked python scripts/verify_azure_security.py
```

The script queries Azure policies, inventories principals/grants, performs rollback-only privilege probes and checks negative logins. It creates no paid resources and enables no services. It returns a nonzero exit code for failed or inconclusive core controls. Auditing/threat-protection gaps remain explicit findings even when the tested core controls pass. The sanitized machine-readable report is stored in ignored `.local/azure/security-verification.json`.

## Integration tests completed without local Docker

The fresh-schema contract passed in a temporary free Azure SQL database. The migration contract exposed a batch-compilation defect: the phone CHECK constraint was bound while the original column was still BIGINT. The repair defers compilation of that fixed constraint until after conversion to VARCHAR. The strengthened test then passed, verifying preflight rejection, complete DDL rollback, record preservation, successful conversion, repeat execution and legacy-password upgrade.

Across the initial run and targeted repair verification, three temporary UUID-named databases were created with free-limit AutoPause protection and deleted after testing. Deletion required an exact resource-ID match and the current run's ownership tag. Existing production/preview schemas were not migrated or reset. The hosted CI job separately passed both integration contracts using an owned disposable LocalDB instance on GitHub's Windows runner; no Azure credentials were supplied. See [hosted verification](CI_AND_TESTING.md#hosted-verification) and [the Docker-free integration instructions](CI_AND_TESTING.md#run-schema-and-migration-integration-without-local-database-software).
