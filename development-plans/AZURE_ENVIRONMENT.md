# Current Azure SQL environment

Verified on **2026-10-31** using the signed-in Azure CLI identity and live SQL connections. This record describes the configured environment; the [complete setup guide](AZURE_SQL_SETUP_GUIDE.md) explains provisioning from scratch.

| Setting | Production | Preview |
| --- | --- | --- |
| Resource group | `EMP-RESOURCE` | `EMP-RESOURCE` |
| Logical server | `sql-emp-db` | `sql-emp-db` |
| Database | `sql-emp-db` | `sql-emp-db-preview` |
| Region | Southeast Asia | Southeast Asia |
| Schema version | 1 | 1 |
| Runtime SQL user | `ems_production_app` | `ems_preview_app` |
| Local runtime configuration | `.env.production` | `.env.preview` |
| Application administrator username | `admin` | `admin` |
| Employee records after verification | 0 | 20 fictional examples |

The existing production database and server were retained. Both databases were confirmed to contain no user tables before application initialization. Preview was created independently, and only preview received the reviewed sample data. Each database now has its own schema and administrator password.

## Start the application

1. Open PowerShell in the repository root.
2. Open `.local/azure/application-accounts.json` privately in your editor. The `preview` and `production` entries each contain `application_username` and `application_password` for console login. They also contain the separate SQL credentials used by their runtime configuration files. Keep this file private.
3. Start preview:

   ```powershell
   uv run ems
   ```

4. Enter the preview application username and password at the console prompts. The password prompt hides input. Use preview for demonstrations and experiments.
5. Exit the application before starting production:

   ```powershell
   uv run ems production
   ```

6. Use the production application's distinct password. Production has no departments, positions, employees or reviews yet. Create departments and positions before entering employees.

The obsolete localhost `.env` was removed. Preview is the default; `production` explicitly selects `.env.production`. With the virtual environment activated, use `ems` or `ems production`. Loading one file does not change process variables or contaminate a later environment selection. An already exported `EMS_CONNECTION_STRING` environment variable still takes precedence; remove that variable if you intend to use the selected file:

```powershell
Remove-Item Env:EMS_CONNECTION_STRING -ErrorAction SilentlyContinue
```

The generated credential file and both runtime configuration files are Git-ignored. Their Windows permissions are limited to the signed-in operator and SYSTEM. Passwords were generated locally and were not printed in command output or committed. ODBC Driver 18 was installed from a signature-verified Microsoft installer. The runtime connection strings require encryption and certificate validation.

## Verified configuration and permissions

Both databases report these settings through the Azure management API:

| Property | Value |
| --- | --- |
| Free limit enabled | `useFreeLimit = true` |
| Free-limit exhaustion | `AutoPause` |
| Compute | General Purpose serverless, `GP_S_Gen5` |
| Minimum / maximum vCores | 0.5 / 2 |
| Data maximum | 32 GiB |
| Backup redundancy | Local |
| API-reported `autoPauseDelay` | 60 minutes; does not override the free-tier rule below |

Microsoft documents a fixed **15-minute** inactivity pause for free-tier databases, regardless of the API-reported value. This record distinguishes the inspected property from the service's documented behavior; no timed pause experiment was conducted. See [free-tier limitations](https://learn.microsoft.com/en-us/azure/azure-sql/database/free-tier#considerations-and-limitations).

`AutoPause` is configured to stop the database at the monthly free allowance rather than enable paid overage. Microsoft documents the allowance and its limits in the [free-tier guide](https://learn.microsoft.com/en-us/azure/azure-sql/database/free-tier). This verification checked resource settings, not a subscription billing statement. Availability can stop when the allowance is exhausted.

The server retains its existing single-client-IP firewall rule. No broad Azure-services firewall rule was added. If your public IP changes, update only the intended client rule through Azure administration. TLS minimum remains 1.2.

Each contained runtime SQL user belongs to `ems_app_runtime` in its own database. This role has DML permissions on the five business/account tables and read permission on the schema version table and reporting view. Live checks confirmed that runtime users are not database owners, cannot create tables, and cannot authenticate to the other environment's database. Console administrator/viewer roles additionally govern application operations; possession of a runtime SQL password still permits direct access to its granted tables.

The 2026-11-01 hardening extension adds six enabled change-journal triggers and eight explicit runtime DENYs on its journal/feature tables. Both environments passed durable-event, rollback, promotion/demotion and tampering-denial checks without changing business fingerprints. Use [the on-demand security review guide](FREE_SECURITY_HARDENING.md); managed Defender and native SQL auditing remain deferred under the free-only requirement.

Initialization and account provisioning used the operator's existing Microsoft Entra administrator identity with an in-memory Azure SQL access token. No server administrator password reset, permanent token file or additional cloud identity was needed. Future schema maintenance should use that operator identity in a trusted SQL administration tool, not the runtime users.

## Live acceptance evidence

- Schema version checks and application administrator authentication passed through both runtime connection strings.
- Preview contained 20 departments, 20 positions, 20 employees, 20 reviews and one administrator account after testing.
- Production contained zero departments, positions, employees and reviews, plus one administrator account.
- Preview ORM checks passed for employee creation, update and removal; review removal with its employee; missing-record results; exact decimal computed compensation; leading-zero phones; SQL injection text stored as data; and reporting for an employee without reviews.
- A temporary viewer could list departments but could not read employees, reviews or reports, or remove an employee. An incorrect password cleared the authenticated session.
- Cross-database login attempts were rejected in both directions.
- Temporary smoke-test records and the temporary viewer were removed; all table counts returned to their baseline.
- Final Azure checks confirmed free-limit protection on both databases and the unchanged firewall rule.

The local operator scripts and machine-readable smoke results are under ignored `.local/azure/`. The original exported Azure template under `.local/template/` was preserved. The old export is not a complete redeployment template and does not contain the newly created preview resource.

The expanded [Azure acceptance suite](../tests/test_azure.py) tests both environments with temporary fixtures enclosed in outer transactions. Every test rolls back its writes and compares fingerprints of all six application tables with their original contents. Fresh-schema and legacy-migration contracts were also separately executed in temporary free Azure databases, which were deleted afterward. See the [testing guide](CI_AND_TESTING.md) and [database security verification](DATABASE_SECURITY_VERIFICATION.md) for current evidence. `EMS_TEST_SERVER_CONNECTION` remains reserved for a dedicated native test server. Hosted CI remains a separate check. Database setup does not deploy an application host.

Opening a database automatically retries resume error 40613 with bounded delays of 5, 10 and 15 seconds. Other errors fail normally, and application writes are never automatically replayed. If resume takes longer, wait and restart. See the [troubleshooting section](AZURE_SQL_SETUP_GUIDE.md#section-14-troubleshooting-and-recovery) for quota, firewall and connection recovery.
