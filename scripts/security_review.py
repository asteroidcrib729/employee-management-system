"""On-demand triage using existing SQL storage; no daemon or paid service."""

import argparse
import json
from datetime import datetime, timezone

from azure_sql import ROOT, AzureSql

TRIGGERS = {
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


def journal_health(connection):
    """Read operator-only metadata, including effective runtime DENY entries."""
    version = connection.exec_driver_sql(
        "SELECT Version FROM dbo.EMS_SecurityFeatures WHERE Feature='CommittedChangeJournal'"
    ).scalar_one_or_none()
    triggers = connection.exec_driver_sql(
        "SELECT name,is_disabled FROM sys.triggers WHERE name LIKE 'EMS_Journal[_]%'"
    ).all()
    denies = set(
        map(
            tuple,
            connection.exec_driver_sql(
                "SELECT OBJECT_NAME(major_id),permission_name,state_desc FROM sys.database_permissions "
                "WHERE grantee_principal_id=DATABASE_PRINCIPAL_ID('ems_app_runtime') "
                "AND major_id IN (OBJECT_ID('dbo.EMS_ChangeJournal'),OBJECT_ID('dbo.EMS_SecurityFeatures'))"
            ).all(),
        )
    )
    expected = {
        (table, verb, "DENY")
        for table in ("EMS_ChangeJournal", "EMS_SecurityFeatures")
        for verb in ("SELECT", "INSERT", "UPDATE", "DELETE")
    }
    return (
        version == 1
        and {row[0] for row in triggers} == TRIGGERS
        and not any(row[1] for row in triggers)
        and denies == expected
    )


def signals(groups, connection_events, *, healthy, free_protected, storage_percent):
    """Return triage categories/counts only, never identifiers or raw SQL text."""
    alerts = []
    if not healthy:
        alerts.append({"signal": "journal_configuration_drift"})
    if not free_protected:
        alerts.append({"signal": "free_limit_protection_missing"})
    if storage_percent >= 80:
        alerts.append({"signal": "database_storage_near_limit"})
    admin_changes = sum(
        row["Count"]
        for row in groups
        if row["ObjectName"] == "Sign_Up"
        and row["SubjectRole"] == "admin"
        and row["Operation"] in ("INSERT", "UPDATE", "DELETE")
    )
    if admin_changes:
        alerts.append(
            {"signal": "administrator_account_changes", "count": admin_changes}
        )
    ddl = sum(
        row["Count"]
        for row in groups
        if row["Operation"] not in ("INSERT", "UPDATE", "DELETE")
    )
    if ddl:
        alerts.append({"signal": "schema_or_permission_changes", "count": ddl})
    bulk = sum(
        row["Count"]
        for row in groups
        if row["ObjectName"] == "Employees"
        and row["Operation"] == "DELETE"
        and row["Count"] >= 5
    )
    if bulk:
        alerts.append({"signal": "employee_bulk_deletion", "count": bulk})
    failed = sum(
        row["event_count"]
        for row in connection_events
        if row["event_subtype_desc"] == "login_failed_for_user"
        and row["event_count"] >= 5
    )
    if failed:
        alerts.append({"signal": "repeated_sql_login_failures", "count": failed})
    return alerts


def review(azure, hours):
    report = {
        "reviewed_utc": datetime.now(timezone.utc).isoformat(),
        "window_hours": hours,
        "mode": "on-demand; no background collection or notification",
        "managed_threat_protection": "deferred: paid service",
        "native_sql_audit": "deferred: no guaranteed free destination",
        "connection_log_warning": "delayed/incomplete diagnostic view, not a complete authentication audit",
        "databases": {},
        "inconclusive": [],
    }
    events = []
    master = azure.database("master")
    try:
        with master.engine.connect() as connection:
            events = [
                dict(row)
                for row in connection.exec_driver_sql(
                    "SELECT TOP(1001) database_name,event_subtype_desc,event_count FROM sys.event_log "
                    "WHERE start_time>=DATEADD(hour,?,SYSUTCDATETIME()) "
                    "AND event_type='connection_failed' AND database_name IN (?,?,'') "
                    "ORDER BY start_time DESC",
                    (-hours, azure.production, azure.production + "-preview"),
                ).mappings()
            ]
        if len(events) > 1000:
            report["inconclusive"].append("Connection diagnostic row limit reached")
            events = events[:1000]
        report["connection_failure_count"] = sum(row["event_count"] for row in events)
        report["unattributed_connection_failure_count"] = sum(
            row["event_count"] for row in events if not row["database_name"]
        )
    except Exception as error:
        report["inconclusive"].append(
            f"Connection diagnostics unavailable: {type(error).__name__}"
        )
    finally:
        master.close()
    for environment in ("preview", "production"):
        name = azure.production + ("-preview" if environment == "preview" else "")
        db = azure.database(name)
        try:
            settings = azure.db("show", "--name", name)
            free_protected = (
                settings.get("useFreeLimit") is True
                and settings.get("freeLimitExhaustionBehavior") == "AutoPause"
            )
            with db.engine.connect() as connection:
                healthy = journal_health(connection)
                groups = [
                    dict(row)
                    for row in connection.exec_driver_sql(
                        "SELECT TOP(1001) ObjectName,Operation,SubjectRole,COUNT_BIG(*) AS [Count], "
                        "DATEADD(minute,DATEDIFF(minute,'20000101',OccurredUtc)/15*15,'20000101') AS BucketUtc "
                        "FROM dbo.EMS_ChangeJournal WHERE OccurredUtc>=DATEADD(hour,?,SYSUTCDATETIME()) "
                        "GROUP BY ObjectName,Operation,SubjectRole, "
                        "DATEADD(minute,DATEDIFF(minute,'20000101',OccurredUtc)/15*15,'20000101') "
                        "ORDER BY BucketUtc DESC",
                        (-hours,),
                    ).mappings()
                ]
                used = connection.exec_driver_sql(
                    "SELECT SUM(CONVERT(bigint,FILEPROPERTY(name,'SpaceUsed')))*8192 FROM sys.database_files WHERE type=0"
                ).scalar_one()
                journal_bytes = connection.exec_driver_sql(
                    "SELECT SUM(used_page_count)*8192 FROM sys.dm_db_partition_stats WHERE object_id=OBJECT_ID('dbo.EMS_ChangeJournal')"
                ).scalar_one()
            if len(groups) > 1000:
                report["inconclusive"].append(
                    f"{environment}: journal group limit reached"
                )
                groups = groups[:1000]
            maximum = settings.get("maxSizeBytes")
            if not maximum or used is None:
                raise RuntimeError("Storage capacity unavailable")
            percent = round(used / maximum * 100, 2)
            matching_events = [
                row for row in events if row["database_name"] in (name, "")
            ]
            report["databases"][environment] = {
                "journal_configuration_healthy": healthy,
                "free_limit_protected": free_protected,
                "database_storage_percent": percent,
                "journal_storage_bytes": journal_bytes,
                "changes_in_window": sum(row["Count"] for row in groups),
                "signals_for_operator_review": signals(
                    groups,
                    matching_events,
                    healthy=healthy,
                    free_protected=free_protected,
                    storage_percent=percent,
                ),
            }
        except Exception as error:
            report["inconclusive"].append(
                f"{environment}: review unavailable: {type(error).__name__}"
            )
        finally:
            db.close()
    # Zero means only that no configured signal was seen in this limited review.
    report["exit_code"] = (
        3
        if report["inconclusive"]
        else (
            2
            if any(
                db["signals_for_operator_review"] for db in report["databases"].values()
            )
            else 0
        )
    )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--hours", type=int, choices=range(1, 169), default=24, metavar="1..168"
    )
    args = parser.parse_args()
    try:
        result = review(AzureSql(), args.hours)
        (ROOT / ".local/azure/security-review.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8"
        )
        print(json.dumps(result, indent=2))
        raise SystemExit(result["exit_code"])
    except Exception as error:
        print(f"Review inconclusive: {type(error).__name__}; credentials not logged")
        raise SystemExit(3) from None
