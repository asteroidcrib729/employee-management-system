"""Install and verify supplemental logging inside the existing free SQL databases."""

import argparse
import json
import secrets

from azure_sql import ROOT, AzureSql
from sqlalchemy import delete
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker
from verify_azure_security import fingerprint

from ems.db import Database
from ems.models import Account, Department
from ems.security import hash_password
from ems.service import Service, User


def verify(azure, environment):
    name = azure.production + ("-preview" if environment == "preview" else "")
    settings = azure.db("show", "--name", name)
    if (
        settings.get("useFreeLimit") is not True
        or settings.get("freeLimitExhaustionBehavior") != "AutoPause"
    ):
        raise RuntimeError("Free-limit protection is required; refusing changes")
    operator = azure.database(name)
    before = fingerprint(operator)
    try:
        operator.script("004_change_journal.sql")
        # Verify both promotion and demotion metadata, with no lasting account.
        username = "journal_" + secrets.token_hex(5)
        with operator.engine.connect() as connection:
            transaction = connection.begin()
            connection.exec_driver_sql("SELECT @@TRANCOUNT")
            db = Database(operator.engine)
            db.sessions = sessionmaker(
                bind=connection,
                expire_on_commit=False,
                join_transaction_mode="create_savepoint",
            )
            try:
                with db.session() as session:
                    session.add(
                        Account(
                            username=username,
                            password=hash_password(secrets.token_hex(32)),
                            role="viewer",
                        )
                    )
                for role in ("admin", "viewer"):
                    with db.session() as session:
                        session.get(Account, username).role = role
                roles = (
                    connection.exec_driver_sql(
                        "SELECT SubjectRole FROM dbo.EMS_ChangeJournal WHERE ObjectName='Sign_Up' AND EntityId=? ORDER BY EventId",
                        (username,),
                    )
                    .scalars()
                    .all()
                )
                if roles != ["viewer", "admin", "admin"]:
                    raise RuntimeError(
                        "Account promotion/demotion journal metadata is incorrect"
                    )
            finally:
                transaction.rollback()
        runtime = Database.connect(ROOT / f".env.{environment}")
        try:
            with runtime.engine.connect() as connection:
                if connection.exec_driver_sql("SELECT DB_NAME()").scalar_one() != name:
                    raise RuntimeError("Wrong runtime target")
                for verb in ("SELECT", "INSERT", "UPDATE", "DELETE"):
                    if (
                        connection.exec_driver_sql(
                            "SELECT HAS_PERMS_BY_NAME('dbo.EMS_ChangeJournal','OBJECT',?)",
                            (verb,),
                        ).scalar_one()
                        != 0
                    ):
                        raise RuntimeError(
                            "Runtime must not read or modify its own journal"
                        )
            suffix = f"{800000 + secrets.randbelow(199998):06d}"
            dept, post, employee = (
                prefix + suffix for prefix in ("DEPT", "POST", "EMP")
            )
            with runtime.engine.connect() as connection:
                transaction = connection.begin()
                connection.exec_driver_sql("BEGIN TRANSACTION")
                try:
                    db = Database(runtime.engine)
                    db.sessions = sessionmaker(
                        bind=connection,
                        expire_on_commit=False,
                        join_transaction_mode="create_savepoint",
                    )
                    service = Service(db)
                    service.user = User("journal-test", "admin")
                    service.add_department(dept, "Journal test", "Test", "2026-11-01")
                    service.add_position(post, "Journal test", dept, "1", "100000", "")
                    values = [
                        employee,
                        "Journal",
                        "Test",
                        "test@example.com",
                        "03001234567",
                        "2026-11-01",
                        "50000.50",
                        "125.25",
                        "2026-11-01",
                        dept,
                        post,
                    ]
                    service.save_employee(*values)
                    values[1] = "Updated"
                    service.save_employee(*values, update=True)
                    service.remove_employee(employee)
                finally:
                    if transaction.is_active:
                        transaction.rollback()
            # Direct writes are denied even though owned triggers can append events.
            for sql in (
                "SELECT TOP(1) EventId FROM dbo.EMS_ChangeJournal",
                "DELETE FROM dbo.EMS_ChangeJournal WHERE 1=0",
                "UPDATE dbo.EMS_ChangeJournal SET Operation=Operation WHERE 1=0",
                "INSERT dbo.EMS_ChangeJournal(StatementId,DatabaseActor,ObjectName,Operation) "
                "SELECT NEWID(),'test','test','INSERT' WHERE 1=0",
            ):
                with runtime.engine.connect() as connection:
                    try:
                        connection.exec_driver_sql(sql)
                    except DBAPIError as error:
                        if "(229)" not in str(error.orig):
                            raise RuntimeError(
                                "Unexpected journal permission error"
                            ) from None
                    else:
                        raise RuntimeError(
                            "Runtime journal access unexpectedly permitted"
                        )
            # Commit an insert/delete pair in ONE transaction: no synthetic business
            # row becomes visible, but two durable metadata events must remain.
            with operator.engine.connect() as connection:
                if (
                    connection.exec_driver_sql(
                        "SELECT COUNT_BIG(*) FROM dbo.EMS_ChangeJournal WHERE EntityId IN (?,?,?)",
                        (dept, post, employee),
                    ).scalar_one()
                    != 0
                ):
                    raise RuntimeError("Rolled-back changes left journal events behind")
            with runtime.engine.begin() as connection:
                # ODBC has already begun its transaction on this first SELECT.
                # A second BEGIN would leave a nested transaction uncommitted.
                if connection.exec_driver_sql("SELECT @@TRANCOUNT").scalar_one() != 1:
                    raise RuntimeError("Exactly one outer transaction required")
                db = Database(runtime.engine)
                db.sessions = sessionmaker(
                    bind=connection,
                    expire_on_commit=False,
                    join_transaction_mode="create_savepoint",
                )
                service = Service(db)
                service.user = User("journal-test", "admin")
                service.add_department(dept, "Journal proof", "Test", "2026-11-01")
                with db.session() as session:
                    session.execute(
                        delete(Department).where(Department.department_id == dept)
                    )
            with operator.engine.connect() as connection:
                recorded = connection.exec_driver_sql(
                    "SELECT Operation,DatabaseActor FROM dbo.EMS_ChangeJournal "
                    "WHERE ObjectName='Departments' AND EntityId=? ORDER BY EventId",
                    (dept,),
                ).all()
                if [row[0] for row in recorded] != ["INSERT", "DELETE"] or any(
                    row[1] != f"ems_{environment}_app" for row in recorded
                ):
                    raise RuntimeError(
                        "Committed runtime change events were not recorded correctly"
                    )
        finally:
            runtime.close()
        if fingerprint(operator) != before:
            raise RuntimeError("Journal installation changed business records")
        with operator.engine.connect() as connection:
            triggers = connection.exec_driver_sql(
                "SELECT name,is_disabled FROM sys.triggers WHERE name LIKE 'EMS_Journal[_]%'"
            ).all()
            if len(triggers) != 6 or any(row[1] for row in triggers):
                raise RuntimeError("Six enabled journal triggers required")
        return {
            "database": name,
            "triggers_enabled": 6,
            "runtime_crud_with_triggers": True,
            "runtime_journal_read_and_write_denied": True,
            "committed_runtime_events_verified": True,
            "rolled_back_events_discarded": True,
            "account_promotion_and_demotion_recorded": True,
            "business_fingerprint_unchanged": True,
        }
    finally:
        operator.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("environment", choices=("preview", "production"))
    args = parser.parse_args()
    try:
        result = verify(AzureSql(), args.environment)
        path = ROOT / f".local/azure/change-journal-{args.environment}.json"
        path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))
    except Exception as error:
        print(f"Journal setup stopped: {type(error).__name__}")
        if isinstance(error, RuntimeError):
            print(str(error))
        raise SystemExit(1) from None
