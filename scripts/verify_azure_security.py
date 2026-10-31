"""Verify Azure SQL configuration and effective runtime security without persisting writes."""

import hashlib
import ipaddress
import json
import re
import secrets
import socket
import time
from datetime import datetime, timezone

import pyodbc
from azure_sql import ROOT, AzureSql
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError

from ems.db import Database, load_environment
from ems.models import (
    Account,
    Department,
    Employee,
    PerformanceReview,
    Position,
    SchemaVersion,
)

MODELS = (Department, Position, Employee, PerformanceReview, Account, SchemaVersion)


def fingerprint(db):
    digest = hashlib.sha256()
    with db.engine.connect() as connection:
        for model in MODELS:
            rows = connection.execute(
                select(model.__table__).order_by(*model.__table__.primary_key.columns)
            ).all()
            digest.update(json.dumps([list(row) for row in rows], default=str).encode())
    return digest.hexdigest()


def permission_probe(db, sql):
    """A successful privileged operation is a failure; every path rolls back."""
    with db.engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.exec_driver_sql(sql)
        except DBAPIError as error:
            codes = set(re.findall(r"\((\d+)\)", str(error.orig)))
            if codes.intersection({"229", "262", "15151", "15247", "15517"}):
                return True
            raise RuntimeError(
                "Security probe returned an unexpected SQL error"
            ) from None
        finally:
            if transaction.is_active:
                transaction.rollback()
    return False


def login_probe(config, certificate=False):
    """Classify a denial separately from network failure or unexpected access."""
    for attempt in range(3):
        try:
            connection = pyodbc.connect(config, timeout=8)
        except pyodbc.Error as error:
            message = str(error).lower()
            codes = re.findall(r"\((-?\d+)\)", message)
            state = error.args[0]
            if not certificate and set(codes).intersection({"18456", "4060", "40532"}):
                return {
                    "denied": True,
                    "sqlstate": state,
                    "reason": "authentication rejected",
                }
            if (
                certificate
                and state in ("08001", "08S01")
                and any(
                    word in message
                    for word in ("certificate", "principal name", "hostname")
                )
            ):
                return {
                    "denied": True,
                    "sqlstate": state,
                    "reason": "certificate hostname rejected",
                }
            if attempt < 2:
                time.sleep(2)
                continue
            return {
                "denied": None,
                "sqlstate": state,
                "codes": codes,
                "reason": "inconclusive connection failure",
            }
        else:
            connection.close()
            return {"denied": False, "reason": "unexpected successful login"}


def certificate_hostname_probe(config, server):
    # ODBC permits the certificate to match Server OR HostNameInCertificate.
    # Use the real endpoint IP so neither accepted hostname matches its certificate.
    address = socket.getaddrinfo(server, 1433, socket.AF_INET, socket.SOCK_STREAM)[0][
        4
    ][0]
    test_config = re.sub(
        r"(?i)(?<=;)SERVER=[^;]*;", f"SERVER=tcp:{address},1433;", config
    )
    if test_config == config:
        raise RuntimeError("Could not construct the certificate hostname test")
    return login_probe(
        test_config + "HostNameInCertificate=ems-security.invalid;", certificate=True
    )


def main():
    azure = AzureSql()
    report = {
        "verified_utc": datetime.now(timezone.utc).isoformat(),
        "findings": [],
        "core_control_failures": [],
        "databases": {},
    }
    server = azure.run("sql", "server", "show", *azure.scope, "--name", azure.server)
    firewall = azure.run(
        "sql", "server", "firewall-rule", "list", *azure.scope, "--server", azure.server
    )
    report["server"] = {
        "minimum_tls": server.get("minimalTlsVersion"),
        "public_network_access": server.get("publicNetworkAccess"),
        "server_firewall_rules": len(firewall),
        "single_ip_rules_only": bool(firewall)
        and all(
            item["startIpAddress"] == item["endIpAddress"]
            and item["startIpAddress"] != "0.0.0.0"
            and not ipaddress.ip_address(item["startIpAddress"]).is_unspecified
            for item in firewall
        ),
    }
    report["server"]["private_endpoint_count"] = len(
        server.get("privateEndpointConnections") or []
    )
    administrators = azure.run(
        "sql", "server", "ad-admin", "list", *azure.scope, "--server", azure.server
    )
    report["server"]["entra_administrator_count"] = len(administrators)
    audit = azure.run(
        "sql", "server", "audit-policy", "show", *azure.scope, "--name", azure.server
    )
    report["server"]["auditing"] = audit.get("state")
    threat = azure.run(
        "sql",
        "server",
        "advanced-threat-protection-setting",
        "show",
        *azure.scope,
        "--name",
        azure.server,
    )
    report["server"]["advanced_threat_protection"] = threat.get("state")
    try:
        roles = azure.run(
            "role",
            "assignment",
            "list",
            "--subscription",
            azure.subscription,
            "--scope",
            server["id"],
            "--include-inherited",
            "--fill-principal-name",
            "false",
        )
        report["server"]["rbac_review"] = "Completed without querying principal names"
    except RuntimeError:
        roles = []
        report["server"]["rbac_review"] = "Unavailable with current CLI identity"
        report["findings"].append(
            "Inherited Azure RBAC assignments could not be enumerated"
        )
    report["server"]["rbac_role_counts"] = {
        name: sum(item["roleDefinitionName"] == name for item in roles)
        for name in sorted({item["roleDefinitionName"] for item in roles})
    }
    if server.get("minimalTlsVersion") not in ("1.2", "1.3"):
        report["findings"].append("Minimum TLS policy is insufficient")
        report["core_control_failures"].append("Minimum TLS policy")
    if not report["server"]["single_ip_rules_only"]:
        report["findings"].append("Review broad or unexpected server firewall rules")
        report["core_control_failures"].append("Server firewall")
    for environment, name, user in (
        ("preview", azure.production + "-preview", "ems_preview_app"),
        ("production", azure.production, "ems_production_app"),
    ):
        print(
            f"Verifying {environment}: configuration, grants, denied operations and isolation",
            flush=True,
        )
        tde = azure.run(
            "sql",
            "db",
            "tde",
            "show",
            *azure.scope,
            "--server",
            azure.server,
            "--database",
            name,
        )
        db_audit = azure.run(
            "sql",
            "db",
            "audit-policy",
            "show",
            *azure.scope,
            "--server",
            azure.server,
            "--name",
            name,
        )
        operator = azure.database(name)
        try:
            with operator.engine.connect() as connection:
                if connection.exec_driver_sql("SELECT DB_NAME()").scalar_one() != name:
                    raise RuntimeError("Wrong database; refusing verification")
                db_firewall = connection.exec_driver_sql(
                    "SELECT start_ip_address,end_ip_address FROM sys.database_firewall_rules"
                ).all()
                grants = connection.exec_driver_sql(
                    "SELECT OBJECT_NAME(major_id),permission_name,state_desc FROM sys.database_permissions "
                    "WHERE grantee_principal_id=DATABASE_PRINCIPAL_ID('ems_app_runtime')"
                ).all()
                memberships = (
                    connection.exec_driver_sql(
                        "SELECT r.name FROM sys.database_role_members m JOIN sys.database_principals r ON m.role_principal_id=r.principal_id "
                        "WHERE m.member_principal_id=DATABASE_PRINCIPAL_ID(?)",
                        (user,),
                    )
                    .scalars()
                    .all()
                )
                direct = connection.exec_driver_sql(
                    "SELECT permission_name,state_desc FROM sys.database_permissions WHERE grantee_principal_id=DATABASE_PRINCIPAL_ID(?)",
                    (user,),
                ).all()
                public_grants = (
                    connection.exec_driver_sql(
                        "SELECT permission_name FROM sys.database_permissions WHERE grantee_principal_id=DATABASE_PRINCIPAL_ID('public') "
                        "AND class=1 AND OBJECT_SCHEMA_NAME(major_id)='dbo' AND state IN ('G','W')"
                    )
                    .scalars()
                    .all()
                )
                constraints = connection.exec_driver_sql(
                    "SELECT COUNT(*) FROM (SELECT is_disabled,is_not_trusted FROM sys.foreign_keys "
                    "UNION ALL SELECT is_disabled,is_not_trusted FROM sys.check_constraints) c WHERE is_disabled=1 OR is_not_trusted=1"
                ).scalar_one()
                weak_hashes = 0
                for value in connection.execute(select(Account.password)).scalars():
                    match = re.fullmatch(
                        r"pbkdf2_sha256\$(\d+)\$[0-9a-f]{32}\$[0-9a-f]{64}", value
                    )
                    weak_hashes += not match or int(match[1]) < 600000
                sql_users = (
                    connection.exec_driver_sql(
                        "SELECT name FROM sys.database_principals WHERE principal_id>4 AND type='S'"
                    )
                    .scalars()
                    .all()
                )
                actual_encryption = connection.exec_driver_sql(
                    "SELECT encrypt_option FROM sys.dm_exec_connections WHERE session_id=@@SPID"
                ).scalar_one()
                encryption_state = connection.exec_driver_sql(
                    "SELECT encryption_state FROM sys.dm_database_encryption_keys WHERE database_id=DB_ID()"
                ).scalar_one()
                journal_version = connection.exec_driver_sql(
                    "SELECT Version FROM dbo.EMS_SecurityFeatures WHERE Feature='CommittedChangeJournal'"
                ).scalar_one_or_none()
                journal_triggers = connection.exec_driver_sql(
                    "SELECT name,is_disabled FROM sys.triggers WHERE name LIKE 'EMS_Journal[_]%'"
                ).all()
            expected = {
                (table, operation, "GRANT")
                for table in (
                    "Departments",
                    "Positions",
                    "Employees",
                    "PerformanceReview",
                    "Sign_Up",
                )
                for operation in ("SELECT", "INSERT", "UPDATE", "DELETE")
            }
            expected |= {
                (table, "SELECT", "GRANT")
                for table in ("EMS_SchemaVersion", "EmployeeManagementView")
            }
            expected |= {
                (table, operation, "DENY")
                for table in ("EMS_ChangeJournal", "EMS_SecurityFeatures")
                for operation in ("SELECT", "INSERT", "UPDATE", "DELETE")
            }
            config = load_environment(ROOT / f".env.{environment}")[
                "EMS_CONNECTION_STRING"
            ]
            runtime = Database.connect(ROOT / f".env.{environment}")
            try:
                before = fingerprint(runtime)
                with runtime.engine.connect() as connection:
                    actual, identity, owner = connection.exec_driver_sql(
                        "SELECT DB_NAME(),USER_NAME(),IS_MEMBER('db_owner')"
                    ).one()
                    effective = (
                        connection.exec_driver_sql(
                            "SELECT permission_name FROM sys.fn_my_permissions(NULL,'DATABASE')"
                        )
                        .scalars()
                        .all()
                    )
                    dangerous = {}
                    for permission in (
                        "CONTROL",
                        "ALTER ANY ROLE",
                        "ALTER ANY USER",
                        "CREATE TABLE",
                        "ALTER ANY SCHEMA",
                    ):
                        dangerous[permission] = connection.exec_driver_sql(
                            "SELECT HAS_PERMS_BY_NAME(DB_NAME(),'DATABASE',?)",
                            (permission,),
                        ).scalar_one()
                    dangerous["IMPERSONATE dbo"] = connection.exec_driver_sql(
                        "SELECT HAS_PERMS_BY_NAME('dbo','USER','IMPERSONATE')"
                    ).scalar_one()
                denied_create = permission_probe(
                    runtime,
                    f"CREATE TABLE dbo.[__ems_security_{secrets.token_hex(8)}] (id int)",
                )
                denied_escalation = permission_probe(
                    runtime, f"ALTER ROLE [db_owner] ADD MEMBER [{user}]"
                )
                denied_impersonation = permission_probe(
                    runtime, "EXECUTE AS USER='dbo'; REVERT;"
                )
                if fingerprint(runtime) != before:
                    raise RuntimeError(
                        "Security verification changed application records"
                    )
                other = (
                    azure.production
                    if environment == "preview"
                    else azure.production + "-preview"
                )
                # Generated runtime passwords do not contain semicolons; target only the DATABASE field.
                wrong = re.sub(
                    r"(?i)(?<=;)DATABASE=[^;]*;", f"DATABASE={other};", config
                )
                if wrong == config:
                    raise RuntimeError("Could not select the isolation test database")
                cross_probe = login_probe(wrong)
                bad = "Invalid9!" + secrets.token_hex(24)
                wrong_password = re.sub(
                    r"(?i)(?<=;)PWD=\{[^}]*\};",
                    f"PWD={{{bad}}};",
                    config,
                )
                if wrong_password == config:
                    raise RuntimeError(
                        "Could not construct the incorrect-password test"
                    )
                password_probe = login_probe(wrong_password)
                certificate_probe = certificate_hostname_probe(
                    config, azure.server + ".database.windows.net"
                )
                result = {
                    "database": name,
                    "tde": tde.get("state"),
                    "operator_connection_encrypted": actual_encryption,
                    "data_encryption_state": encryption_state,
                    "client_encrypt_required": ";Encrypt=yes;" in config,
                    "client_certificate_validation": ";TrustServerCertificate=no;"
                    in config,
                    "runtime_identity_correct": (actual, identity, owner)
                    == (name, user, 0),
                    "runtime_roles": memberships,
                    "only_expected_runtime_role": memberships == ["ems_app_runtime"],
                    "no_direct_privileged_grants": all(
                        tuple(row) == ("CONNECT", "GRANT") for row in direct
                    ),
                    "runtime_direct_permissions": [list(row) for row in direct],
                    "effective_database_permissions": effective,
                    "dangerous_database_permissions": dangerous,
                    "table_grants_exactly_expected": set(map(tuple, grants))
                    == expected,
                    "no_public_business_table_grants": not public_grants,
                    "only_expected_sql_user": sql_users == [user],
                    "database_firewall_rules": len(db_firewall),
                    "database_firewall_narrow": all(
                        row[0] == row[1] and row[0] != "0.0.0.0" for row in db_firewall
                    ),
                    "all_constraints_enabled_and_trusted": constraints == 0,
                    "all_password_hashes_current": weak_hashes == 0,
                    "ddl_denied": denied_create,
                    "role_escalation_denied": denied_escalation,
                    "dbo_impersonation_denied": denied_impersonation,
                    "cross_database_login_denied": cross_probe["denied"],
                    "incorrect_sql_password_denied": password_probe["denied"],
                    "certificate_mismatch_denied": certificate_probe["denied"],
                    "negative_login_details": {
                        "cross_database": cross_probe,
                        "incorrect_password": password_probe,
                        "certificate_mismatch": certificate_probe,
                    },
                    "data_fingerprint_unchanged": True,
                    "database_auditing": db_audit.get("state"),
                    "committed_change_journal_enabled": journal_version == 1
                    and {row[0] for row in journal_triggers}
                    == {
                        "EMS_Journal_" + name
                        for name in (
                            "Departments",
                            "Positions",
                            "Employees",
                            "PerformanceReview",
                            "Sign_Up",
                            "DDL",
                        )
                    }
                    and not any(row[1] for row in journal_triggers),
                }
                report["databases"][environment] = result
                required = [
                    result[key]
                    for key in (
                        "client_encrypt_required",
                        "client_certificate_validation",
                        "runtime_identity_correct",
                        "only_expected_runtime_role",
                        "no_direct_privileged_grants",
                        "database_firewall_narrow",
                        "table_grants_exactly_expected",
                        "no_public_business_table_grants",
                        "only_expected_sql_user",
                        "all_constraints_enabled_and_trusted",
                        "all_password_hashes_current",
                        "ddl_denied",
                        "role_escalation_denied",
                        "dbo_impersonation_denied",
                        "cross_database_login_denied",
                        "incorrect_sql_password_denied",
                        "certificate_mismatch_denied",
                        "committed_change_journal_enabled",
                    )
                ]
                if (
                    not all(required)
                    or any(value != 0 for value in dangerous.values())
                    or tde.get("state") != "Enabled"
                    or encryption_state != 3
                    or str(actual_encryption).upper() != "TRUE"
                ):
                    report["findings"].append(
                        f"{environment}: a core security control failed; inspect recorded results"
                    )
                    report["core_control_failures"].append(environment)
                if (
                    db_audit.get("state") != "Enabled"
                    and audit.get("state") != "Enabled"
                ):
                    report["findings"].append(
                        f"{environment}: native SQL auditing deferred under free-only policy; committed-change journal is supplemental"
                    )
            finally:
                runtime.close()
        finally:
            operator.close()
    if threat.get("state") != "Enabled":
        report["findings"].append(
            "Managed advanced threat protection deferred under free-only policy; no paid plan or trial enabled"
        )
    path = ROOT / ".local/azure/security-verification.json"
    report["core_controls_passed"] = not report["core_control_failures"]
    report["full_production_security_certification"] = False
    report["monitoring_mode"] = (
        "on-demand; no collection or alerts while the operator is offline"
    )
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)
    return 0 if report["core_controls_passed"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(
            f"Security verification stopped: {type(error).__name__}; no credentials logged",
            flush=True,
        )
        if isinstance(error, RuntimeError):
            print(str(error), flush=True)
        raise SystemExit(1) from None
