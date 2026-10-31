# Azure SQL: free production and preview database setup

Verified against Microsoft documentation on **2026-10-31**. Run repository commands from its root in PowerShell. This guide creates two independent **Azure SQL Databases**, a managed service compatible with SQL Server. It does not deploy a SQL Server virtual machine or an application host.

I use `ems-production` for the deployed environment and `ems-preview` for staging and experiments. “Preview” is an application environment name, not a requirement to use an Azure preview product. Both databases use the same supported schema.

For this workstation's completed setup, see [the current Azure environment and launch instructions](AZURE_ENVIRONMENT.md). Its actual names are `sql-emp-db` and `sql-emp-db-preview`; the names below are reusable examples.

## Navigation

- [Section 01: Understand the free limits](#section-01-understand-the-free-limits)
- [Section 02: Prepare accounts and tools](#section-02-prepare-accounts-and-tools)
- [Section 03: Create the resource group and logical server](#section-03-create-the-resource-group-and-logical-server)
- [Section 04: Create the production database](#section-04-create-the-production-database)
- [Section 05: Create the preview database](#section-05-create-the-preview-database)
- [Section 06: Restrict network access](#section-06-restrict-network-access)
- [Section 07: Verify billing protection](#section-07-verify-billing-protection)
- [Section 08: Prepare local connection files](#section-08-prepare-local-connection-files)
- [Section 09: Initialize and test preview](#section-09-initialize-and-test-preview)
- [Section 10: Initialize production](#section-10-initialize-production)
- [Section 11: Create separate runtime database users](#section-11-create-separate-runtime-database-users)
- [Section 12: Validate environment isolation](#section-12-validate-environment-isolation)
- [Section 13: Operate within the allowance](#section-13-operate-within-the-allowance)
- [Section 14: Troubleshooting and recovery](#section-14-troubleshooting-and-recovery)
- [Section 15: Optional Azure CLI database creation](#section-15-optional-azure-cli-database-creation)

## Section 01: Understand the free limits

Microsoft currently allows up to ten free General Purpose serverless databases per eligible subscription. Each database receives its own monthly allowance:

| Item | Per database |
| --- | --- |
| Compute | 100,000 vCore-seconds |
| Data | 32 GB |
| Backup storage | 32 GB |
| Duration | Subscription lifetime, subject to the offer's conditions |

The per-database allocation is also described in [Microsoft's free-offer announcement](https://techcommunity.microsoft.com/blog/azuresqlblog/introducing-the-enhanced-azure-sql-database-free-offer-now-generally-available/4372418).

Select **Auto-pause the database until next month** when the free amount is exhausted. Do not select **Continue using database for additional charges**. The allowance renews monthly; it is not an unlimited always-on database. [Microsoft free-tier documentation](https://learn.microsoft.com/en-us/azure/azure-sql/database/free-tier)

The free amount has **no SLA**. Microsoft primarily recommends it for development and proofs of concept. A production-named database is suitable here only if your small project can tolerate interruptions and quota exhaustion. Critical production availability needs a separately funded service. Students Starter subscriptions are ineligible; unused compute does not roll over. [Microsoft free-tier FAQ](https://learn.microsoft.com/en-us/azure/azure-sql/database/free-tier-faq)

These settings cover the databases. Other Azure resources and optional services have their own prices. This walkthrough does not enable paid application hosting, private endpoints, log destinations, or security add-ons.

- [ ] I accept the availability limits and will keep paid overages disabled.

## Section 02: Prepare accounts and tools

1. Sign in to the [Azure portal](https://portal.azure.com/) and select the intended subscription. Complete any identity or billing verification Azure requires; a free database does not remove subscription eligibility requirements.
2. Confirm you have permission to create the resources. Azure resource permissions and SQL database permissions are separate. [Database creation permissions](https://learn.microsoft.com/en-us/azure/azure-sql/database/single-database-create-quickstart#permissions)
3. Install [SQL Server Management Studio](https://learn.microsoft.com/en-us/ssms/install/install) and [Microsoft ODBC Driver 18](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server). Installing `pyodbc` alone does not install Microsoft's system driver.
4. In this repository, install the exact interpreter and locked dependencies:

   ```powershell
   uv python install 3.14.7
   uv sync --locked
   uv run --locked python --version
   uv run --locked python -c "import pyodbc; print(pyodbc.drivers())"
   ```

5. Confirm Python reports `3.14.7` and the driver list contains `ODBC Driver 18 for SQL Server`.
6. Keep credentials in a password manager. Never paste passwords into chat, commits, screenshots, or command-line arguments.

- [ ] Subscription access, Python and the ODBC driver are ready.

## Section 03: Create the resource group and logical server

Use this worksheet, replacing the server placeholder with a globally unique name:

| Resource | Example |
| --- | --- |
| Resource group | `rg-ems` |
| Logical SQL server | `ems-sql-<unique-suffix>` |
| Server endpoint | `ems-sql-<unique-suffix>.database.windows.net` |
| Production database | `ems-production` |
| Preview database | `ems-preview` |

1. Create the resource group in your chosen Azure region.
2. Open **SQL servers** in the portal and create a logical server in that group. You can also create it from the database wizard's **Server > Create new** form.
3. Choose the appropriate region and a unique server name.
4. For this walkthrough, enable SQL authentication and create a strong server administrator login. If you choose Microsoft Entra-only authentication instead, use an Entra authentication connection configuration throughout; the SQL-password examples below will not work unchanged.
5. Save the administrator credentials privately. This is the database operator identity, not an application login.
6. Do not create a VM, Managed Instance, elastic pool, replica, or extra paid service for this walkthrough.

Microsoft documents the server form and the differences between development and production presets in its [single-database quickstart](https://learn.microsoft.com/en-us/azure/azure-sql/database/single-database-create-quickstart). Avoid a production preset that replaces the free configuration with provisioned compute or a different backup setting.

- [ ] The logical server exists and I have recorded its endpoint.

## Section 04: Create the production database

1. Open the [Azure SQL hub](https://aka.ms/azuresqlhub).
2. In **Create a database**, choose **Start free**. An older portal experience may call this **Apply offer**.
3. Select your subscription, `rg-ems`, the logical server, and database name `ems-production`.
4. Verify the free General Purpose serverless configuration, monthly-limit auto-pause behavior, and zero estimated monthly database cost before creating it.
5. Choose **Review + create**, verify the summary, then **Create**. If the free option or zero-cost configuration is unavailable, stop and resolve eligibility; do not substitute a paid database.

Use the [current free-tier creation instructions](https://learn.microsoft.com/en-us/azure/azure-sql/database/free-tier#create-a-database) if portal labels change.

- [ ] `ems-production` exists with the free configuration.

## Section 05: Create the preview database

1. Start a second new database through the free creation path.
2. Select the same subscription, resource group and logical server.
3. Name it `ems-preview` and independently verify the same free settings.
4. Review and create it.
5. Record both database names beside their intended connection-file names. Do not create preview by copying or restoring production: the free tier supports new databases, and free database copies/restores have restrictions. [Free-tier technical restrictions](https://learn.microsoft.com/en-us/azure/azure-sql/database/free-tier-faq#technical-questions)

Preview will receive fictional seed data. Production will start empty. Never copy private employee data into a preview environment for this setup.

- [ ] Both environments exist as separate databases.

## Section 06: Restrict network access

1. Open the logical server's **Networking** page.
2. For local development, use its public endpoint with **selected networks** and add your current public IPv4 address as a single-address firewall rule.
3. Keep **Allow Azure services and resources to access this server** disabled. It is broader than allowing only your own application.
4. Save. If your public IP changes, update the rule rather than opening a wide IP range.
5. For a future hosted application, add only its documented outbound addresses. A host with unpredictable outbound IPs needs a separate networking decision before deployment.
6. In SSMS, connect to the endpoint using SQL authentication, enable encryption and leave server-certificate trust bypass disabled. Under connection properties, specify `ems-preview` explicitly.
7. Run:

   ```sql
   SELECT DB_NAME() AS DatabaseName, USER_NAME() AS DatabaseUser;
   ```

8. Confirm the target is `ems-preview`. Disconnect when finished.

The firewall determines network reachability; credentials still determine database access. [Microsoft firewall documentation](https://learn.microsoft.com/en-us/azure/azure-sql/database/firewall-configure)

- [ ] Access is restricted and the first connection reached the intended database.

## Section 07: Verify billing protection

For **each** database, open **Compute + storage** and its overview/resource configuration. Record that the free limit is enabled and exhaustion behavior remains auto-pause. Keep the supported local backup configuration; do not enable paid overages to obtain extra features.

In **Cost Management > Cost analysis**, filter to `rg-ems` and review actual and forecast charges. If available, create a small monthly budget with email notifications as an extra reminder. A budget is **an alert, not a spending cap**, and reported costs can lag. The database's own free-limit behavior is the relevant overage control. [Microsoft budget behavior](https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/tutorial-acm-create-budgets)

Do not enable an optional paid feature or trial without reviewing its ongoing cost. If an organization policy adds mandatory paid resources, this walkthrough cannot promise a zero-cost total for that subscription.

- [ ] Both databases have auto-pause overage protection and I checked the cost summary.

## Section 08: Prepare local connection files

Create these four **ignored local files**; never overwrite existing credentials without reviewing them:

| File | Identity and purpose |
| --- | --- |
| `.env.preview.admin` | Operator credentials, preview initialization only |
| `.env.production.admin` | Operator credentials, production initialization only |
| `.env.preview` | Preview runtime user created in Section 11 |
| `.env.production` | Production runtime user created in Section 11 |

Place one `EMS_CONNECTION_STRING=...` line in each administrator file. Replace every placeholder privately:

```dotenv
# .env.preview.admin
EMS_CONNECTION_STRING=DRIVER={ODBC Driver 18 for SQL Server};SERVER=tcp:<server>.database.windows.net,1433;DATABASE=ems-preview;UID=<server-admin>;PWD={<admin-password>};Encrypt=yes;TrustServerCertificate=no;
```

```dotenv
# .env.production.admin
EMS_CONNECTION_STRING=DRIVER={ODBC Driver 18 for SQL Server};SERVER=tcp:<server>.database.windows.net,1433;DATABASE=ems-production;UID=<server-admin>;PWD={<admin-password>};Encrypt=yes;TrustServerCertificate=no;
```

These are ODBC connection strings, not SQLAlchemy URL strings. The application constructs the SQLAlchemy URL safely. ODBC braces preserve password semicolons; escape a literal closing brace inside a braced password by doubling it. Keep TLS certificate verification enabled for Azure. [ODBC connection-string syntax](https://learn.microsoft.com/en-us/sql/odbc/reference/syntax/sql-driver-connect-function)

Before switching files, check for a process override without printing its value:

```powershell
if (Test-Path Env:EMS_CONNECTION_STRING) {
    throw 'A process EMS_CONNECTION_STRING overrides local files. Review and remove that override before selecting an environment.'
}
git check-ignore .env.preview.admin .env.production.admin .env.preview .env.production
```

If runtime files do not exist yet, create them in Section 11 before checking those two paths. The `--env-file` argument selects a file; a missing explicit file fails rather than falling back to another environment.

- [ ] Administrator files point to the correct databases and no stale override is active.

## Section 09: Initialize and test preview

Run the following against the **new, empty preview database**:

```powershell
uv run --locked ems --env-file .env.preview.admin --init-db
uv run --locked ems --env-file .env.preview.admin --create-admin
uv run --locked ems --env-file .env.preview.admin --seed-demo
uv run --locked ems --env-file .env.preview.admin
```

1. Each setup command should exit successfully. If one fails, investigate before continuing.
2. The administrator command prompts for an application username and a confirmed 12-128-character password. This account is stored in `Sign_Up` and is separate from Azure/SQL authentication.
3. Sign in and list departments, positions, employees and reviews. Sample data should include twenty records in each business table.
4. Check the employee report. Create, update and remove a temporary employee to exercise the complete preview flow.
5. Exit the application. Repeating the seed inserts missing IDs only; it never replaces an existing employee's name or salary.

Do not use `--migrate` for a fresh Azure database. That command is specifically for the original coursework schema. Existing-data migration requires its own backup, reconciliation and transfer plan; see the [repository migration instructions](../README.md#existing-coursework-database).

- [ ] Preview initialization, login and employee operations work.

## Section 10: Initialize production

After preview acceptance, run only these production setup commands:

```powershell
uv run --locked ems --env-file .env.production.admin --init-db
uv run --locked ems --env-file .env.production.admin --create-admin
```

Use a distinct application administrator password. **Do not seed production.** In SSMS, open a new connection explicitly targeting `ems-production` and verify:

```sql
SELECT DB_NAME() AS DatabaseName;
SELECT Version FROM dbo.EMS_SchemaVersion;
SELECT COUNT_BIG(*) AS EmployeeCount FROM dbo.Employees;
```

Expected results are database `ems-production`, schema version `1` and zero employees. Disconnect afterward.

- [ ] Production is initialized, its first account exists, and business data is empty.

## Section 11: Create separate runtime database users

Use the server administrator in SSMS. First connect directly to **`ems-preview`** and verify `DB_NAME()` before executing this script. Replace the password placeholder using a unique secret; escape SQL string quotes as needed. Do not save the completed script to Git.

```sql
IF DB_NAME() <> N'ems-preview'
    THROW 51000, 'Wrong database for preview user setup.', 1;

CREATE USER [ems_preview_app] WITH PASSWORD = '<unique-preview-runtime-password>';
CREATE ROLE [ems_app_runtime];
GRANT SELECT, INSERT, UPDATE, DELETE ON OBJECT::dbo.Departments TO [ems_app_runtime];
GRANT SELECT, INSERT, UPDATE, DELETE ON OBJECT::dbo.Positions TO [ems_app_runtime];
GRANT SELECT, INSERT, UPDATE, DELETE ON OBJECT::dbo.Employees TO [ems_app_runtime];
GRANT SELECT, INSERT, UPDATE, DELETE ON OBJECT::dbo.PerformanceReview TO [ems_app_runtime];
GRANT SELECT, INSERT, UPDATE, DELETE ON OBJECT::dbo.Sign_Up TO [ems_app_runtime];
GRANT SELECT ON OBJECT::dbo.EMS_SchemaVersion TO [ems_app_runtime];
GRANT SELECT ON OBJECT::dbo.EmployeeManagementView TO [ems_app_runtime];
ALTER ROLE [ems_app_runtime] ADD MEMBER [ems_preview_app];
```

Then disconnect, connect directly to **`ems-production`**, verify its name, and run a second copy with these changes:

1. Change the guard to `DB_NAME() <> N'ems-production'` and its error message to production.
2. Replace both occurrences of `ems_preview_app` with `ems_production_app`.
3. Supply a different production runtime password.
4. Keep the role and object grants unchanged; roles are scoped to each database.

These are database-contained users. They need not be created in `master`, and each connection must name its database. [Microsoft account model](https://learn.microsoft.com/en-us/azure/azure-sql/database/logins-create-manage), [CREATE USER](https://learn.microsoft.com/en-us/sql/t-sql/statements/create-user-transact-sql), [object grants](https://learn.microsoft.com/en-us/sql/t-sql/statements/grant-object-permissions-transact-sql)

Create the runtime files:

```dotenv
# .env.preview
EMS_CONNECTION_STRING=DRIVER={ODBC Driver 18 for SQL Server};SERVER=tcp:<server>.database.windows.net,1433;DATABASE=ems-preview;UID=ems_preview_app;PWD={<preview-runtime-password>};Encrypt=yes;TrustServerCertificate=no;
```

```dotenv
# .env.production
EMS_CONNECTION_STRING=DRIVER={ODBC Driver 18 for SQL Server};SERVER=tcp:<server>.database.windows.net,1433;DATABASE=ems-production;UID=ems_production_app;PWD={<production-runtime-password>};Encrypt=yes;TrustServerCertificate=no;
```

Runtime users have no schema-change or server-administration grants. Use operator files only for maintenance. Application administrator/viewer permissions still apply inside the console; a person holding a runtime SQL password can bypass console permissions by accessing its granted tables directly. Protect these files with operating-system account permissions.

- [ ] Each database has a different runtime user and password.

## Section 12: Validate environment isolation

1. Start preview using runtime credentials:

   ```powershell
   uv run ems
   ```

2. Sign in, confirm sample records are visible, and exit.
3. Start production using runtime credentials:

   ```powershell
   uv run ems production
   ```

4. Sign in with the production application account. Confirm employee lists remain empty, then exit.
5. In SSMS, test the preview runtime user with `ems-production` as its connection database. Authentication should fail. Repeat with the production runtime user targeting preview. If either succeeds, review users/grants before deployment.
6. Use only preview connection settings in future preview deployments. Supply only production runtime settings to the intended production deployment. Never run integration tests against either cloud database: `EMS_TEST_SERVER_CONNECTION` is reserved for a dedicated disposable test server.
7. Confirm all four local secret files are ignored with `git check-ignore` and review `git status --short` before publishing source.
8. Follow the [free-only hardening guide](FREE_SECURITY_HARDENING.md) to install and verify the committed-change journal in preview, then production. Review its monitoring limitations and real-data prerequisites. The existing configured environments already have this extension; a new database does not receive it from `--init-db` alone.

- [ ] Runtime access works and cross-environment access is denied.

## Section 13: Operate within the allowance

Close SSMS, Object Explorer, query editors and application sessions after use. Idle open sessions can prevent normal serverless pausing. The application uses short ORM sessions, SQLAlchemy `NullPool` and disabled pyodbc pooling so it does not retain idle database connections. Do not add keep-alive pings or a frequent uptime query. [Serverless pause/resume behavior](https://learn.microsoft.com/en-us/azure/azure-sql/database/serverless-tier-auto-pause-resume)

Review each database's **Free amount remaining** metric and its resource cost regularly. Distinguish ordinary idle pausing, which resumes on demand, from monthly-limit exhaustion, which intentionally makes the database unavailable until renewal. [Free usage monitoring](https://learn.microsoft.com/en-us/azure/azure-sql/database/free-tier#track-free-usage)

The free configuration restricts backup retention and redundancy: plan around seven-day PITR and local backups, without assuming long-term retention or a free restore target. Free databases cannot be copied or restored into another free database. Review recovery costs before a restore exercise. [Free-tier restrictions](https://learn.microsoft.com/en-us/azure/azure-sql/database/free-tier-faq#technical-questions)

- [ ] I have a usage-review routine and an acceptable recovery plan.

## Section 14: Troubleshooting and recovery

| Symptom | Next action |
| --- | --- |
| Free option missing or estimated cost is nonzero | Stop creation. Check subscription eligibility, quota, region offerings and selected configuration. |
| Driver missing | Install ODBC Driver 18, restart the terminal, and repeat the driver-list command. |
| Connection blocked | Verify your current public IP rule, endpoint and database name. Keep the firewall narrow. |
| SQL authentication fails | Confirm the selected file, username, password and exact database. A contained user cannot authenticate to an unrelated database. |
| Runtime works in one environment only | Verify that environment's contained user and grants; do not reuse the other environment's password. |
| First connection after inactivity fails | Opening the database retries resume error 40613 up to three times with 5, 10 and 15-second waits. If it still fails, wait and restart. Application writes are never automatically replayed. |
| Database inaccessible later in the month | Check free allowance exhaustion. Keep overage billing off if zero cost is mandatory and wait for monthly renewal. |
| Schema check fails | Use the correct operator file and initialization path; do not grant runtime users database-owner privileges to hide a setup problem. |
| Certificate error | Verify endpoint, system clock and trusted certificate chain. Keep Azure certificate validation enabled. |
| Unexpected charges | Inspect resources and features in Cost analysis. Recheck free-limit behavior on both databases and any separately billed services. |

Resume guidance: [Microsoft serverless troubleshooting](https://learn.microsoft.com/en-us/azure/azure-sql/database/serverless-tier-auto-pause-resume#troubleshooting-auto-resume-connectivity).

When retiring preview, verify the resource's exact name and recoverable data before deleting it in the portal. Do not delete a shared server or resource group to remove a single database. Production deletion and restore planning require their own deliberate maintenance procedure.

- [ ] I can distinguish connection, quota, schema and billing failures.

## Section 15: Optional Azure CLI database creation

Use this **instead of Sections 04 and 05**, only after the resource group and logical server already exist. These commands create cloud resources in your subscription. Adapt the example identifiers for a new deployment; the existing provisioned databases and their verified settings are recorded in [the environment notes](AZURE_ENVIRONMENT.md).

Install the current Azure CLI, sign in, and replace the identifiers:

```powershell
az login
az account list --output table
$azureSubscription = '<subscription-id>'
$azureResourceGroup = 'rg-ems'
$azureServer = '<existing-logical-server-name>'
az account set --subscription $azureSubscription
if ($LASTEXITCODE -ne 0) { throw 'Subscription selection failed.' }
az account show --query '{name:name,id:id}' --output table

foreach ($azureDatabase in @('ems-production', 'ems-preview')) {
    az sql db create --resource-group $azureResourceGroup --server $azureServer --name $azureDatabase --edition GeneralPurpose --family Gen5 --capacity 2 --compute-model Serverless --max-size 32GB --backup-storage-redundancy Local --use-free-limit true --free-limit-exhaustion-behavior AutoPause
    if ($LASTEXITCODE -ne 0) { throw "Creation failed for $azureDatabase. Do not retry without the free-limit flags." }

    $databaseStatus = az sql db show --resource-group $azureResourceGroup --server $azureServer --name $azureDatabase --output json | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) { throw 'Could not verify database settings.' }
    if ($databaseStatus.useFreeLimit -ne $true -or $databaseStatus.freeLimitExhaustionBehavior -ne 'AutoPause') {
        throw 'Free-limit protection was not confirmed. Inspect the portal before proceeding.'
    }
    $databaseStatus | Select-Object name, useFreeLimit, freeLimitExhaustionBehavior
}
```

`--use-free-limit true` and `--free-limit-exhaustion-behavior AutoPause` are essential. A normal serverless database is not automatically free. Confirm current flags using the [Azure CLI reference](https://learn.microsoft.com/en-us/cli/azure/sql/db#az-sql-db-create), then return to Section 06 for networking and the remaining application setup.

- [ ] If I used the CLI route, I verified the returned free-limit properties for both databases.
