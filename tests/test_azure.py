"""Opt-in Azure acceptance tests. Every write is inside a rolled-back transaction.

Set EMS_AZURE_TESTS=1 locally after provisioning. Credentials never enter CI.
"""

import hashlib
import io
import json
import os
import secrets
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from ems import cli
from ems.db import Database
from ems.models import (
    Account,
    Department,
    Employee,
    PerformanceReview,
    Position,
    SchemaVersion,
)
from ems.service import Service

ROOT = Path(__file__).resolve().parents[1]
MODELS = (Department, Position, Employee, PerformanceReview, Account, SchemaVersion)


def fingerprint(database):
    """Hash complete table contents without logging records or password hashes."""
    digest = hashlib.sha256()
    with database.engine.connect() as connection:
        for model in MODELS:
            rows = connection.execute(
                select(model.__table__).order_by(*model.__table__.primary_key.columns)
            ).all()
            digest.update(model.__tablename__.encode())
            digest.update(json.dumps([list(row) for row in rows], default=str).encode())
    return digest.hexdigest()


class AzureAcceptance:
    @classmethod
    def setUpClass(cls):
        # Fail before any write if configuration targets another database or user.
        cls.remote = Database.connect(ROOT / f".env.{cls.environment}")
        cls.remote.check_schema()
        cls.addClassCleanup(cls.remote.close)
        with cls.remote.engine.connect() as connection:
            name, user, owner, ddl = connection.exec_driver_sql(
                "SELECT DB_NAME(), USER_NAME(), IS_MEMBER('db_owner'), "
                "HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'CREATE TABLE')"
            ).one()
        if (name, user, owner, ddl) != (cls.expected_database, cls.expected_user, 0, 0):
            raise AssertionError(
                "Azure target or runtime permissions differ from the approved environment"
            )
        path = Path(
            os.environ.get(
                "EMS_AZURE_CREDENTIAL_FILE",
                ROOT / ".local/azure/application-accounts.json",
            )
        )
        account = json.loads(path.read_text(encoding="utf-8"))[cls.environment]
        cls.username = account["application_username"]
        cls.password = account["application_password"]
        cls.initial_fingerprint = fingerprint(cls.remote)
        cls.addClassCleanup(cls.assert_unchanged)

    @classmethod
    def assert_unchanged(cls):
        if fingerprint(cls.remote) != cls.initial_fingerprint:
            raise AssertionError("Database records changed during acceptance testing")

    def setUp(self):
        self.connection = self.remote.engine.connect()
        self.addCleanup(self.connection.close)
        self.transaction = self.connection.begin()
        # SQL Server SAVE TRANSACTION requires a real outer transaction.
        self.connection.exec_driver_sql("BEGIN TRANSACTION")
        self.addCleanup(self.restore)
        self.db = Database(self.remote.engine)
        self.db.sessions = sessionmaker(
            bind=self.connection,
            expire_on_commit=False,
            join_transaction_mode=(
                "rollback_only"
                if self._testMethodName.startswith("test_database_")
                else "create_savepoint"
            ),
        )
        self.service = Service(self.db)
        self.assertTrue(self.service.login(self.username, self.password))
        suffix = f"{secrets.randbelow(199998) + 800000:06d}"
        self.dept, self.post, self.emp, self.rev = (
            prefix + suffix for prefix in ("DEPT", "POST", "EMP", "REV")
        )
        self.viewer = "test_" + secrets.token_hex(5)
        self.values = [
            self.emp,
            "Acceptance",
            "Fixture",
            "fixture@example.com",
            "03001234567",
            "2026-10-31",
            "50000.50",
            "125.25",
            "2026-10-31",
            self.dept,
            self.post,
        ]
        self.service.add_department(self.dept, "Acceptance", "Test", "2026-10-31")
        self.service.add_position(self.post, "Acceptance", self.dept, "1", "100000", "")
        self.service.save_employee(*self.values)

    def restore(self):
        # A SQL constraint can abort the server transaction; rollback is still safe.
        if self.transaction.is_active:
            self.transaction.rollback()
        self.connection.close()
        self.assert_unchanged()

    def test_employee_crud_compensation_report_and_review_removal(self):
        with self.db.session() as session:
            row = session.get(Employee, self.emp)
            self.assertEqual(row.phone, "03001234567")
            self.assertEqual(row.salary, Decimal("50000.50"))
            self.assertEqual(row.annual, Decimal("601509.00"))
        report = [r for r in self.service.list_records("report")[1] if r[0] == self.emp]
        self.assertEqual(len(report), 1)
        self.assertIsNone(report[0][8])
        self.service.add_review(self.rev, self.emp, "2026-10-31", "Acceptance", "7")
        self.values[1] = "Robert'); DROP TABLE Employees;--"
        self.assertTrue(self.service.save_employee(*self.values, update=True))
        with self.db.session() as session:
            self.assertEqual(session.get(Employee, self.emp).first, self.values[1])
        self.assertTrue(self.service.remove_employee(self.emp))
        self.assertFalse(self.service.remove_employee(self.emp))
        self.assertFalse(self.service.save_employee(*self.values, update=True))
        with self.db.session() as session:
            self.assertIsNone(session.get(PerformanceReview, self.rev))

    def test_account_creation_authentication_and_all_viewer_permissions(self):
        with self.assertRaises(PermissionError):
            Service(self.db).bootstrap_admin(self.viewer, self.password)
        self.service.create_user(self.viewer, self.password)
        viewer = Service(self.db)
        self.assertTrue(viewer.login(self.viewer, self.password))
        for kind in ("departments", "positions"):
            self.assertTrue(viewer.list_records(kind)[1])
        self.assertNotIn("MinSalary", viewer.list_records("positions")[0])
        for kind in ("employees", "reviews", "report"):
            with self.assertRaises(PermissionError):
                viewer.list_records(kind)
        operations = [
            lambda: viewer.add_department(self.dept, "X", "X", "2026-10-31"),
            lambda: viewer.add_position(self.post, "X", self.dept, "1", "2", ""),
            lambda: viewer.save_employee(*self.values),
            lambda: viewer.remove_employee(self.emp),
            lambda: viewer.add_review(self.rev, self.emp, "2026-10-31", "", "7"),
            lambda: viewer.create_user("forbidden", self.password),
        ]
        for operation in operations:
            with self.assertRaises(PermissionError):
                operation()
        self.assertFalse(viewer.login(self.viewer, "incorrect password 123"))
        self.assertIsNone(viewer.user)

    def test_database_duplicate_constraint_rolls_back(self):
        with self.assertRaises(IntegrityError):
            self.service.save_employee(*self.values)

    def test_database_department_assignment_constraint_rolls_back(self):
        # Position and employee departments must agree, even with direct ORM access.
        with self.assertRaises(IntegrityError), self.db.session() as session:
            session.get(Employee, self.emp).department_id = "DEPT000000"

    def test_database_salary_constraint_rolls_back(self):
        with self.assertRaises(IntegrityError), self.db.session() as session:
            session.get(Employee, self.emp).bonus = Decimal("-1")

    def test_database_review_constraint_rolls_back(self):
        with self.assertRaises(IntegrityError), self.db.session() as session:
            session.add(
                PerformanceReview(
                    review_id=self.rev,
                    employee_id=self.emp,
                    reviewed=date(2026, 10, 31),
                    comments=None,
                    rating=10,
                )
            )

    def test_interrupted_transaction_recovers_and_validation_rejects_input(self):
        with self.assertRaises(KeyboardInterrupt), self.db.session() as session:
            session.get(Employee, self.emp).first = "Uncommitted"
            session.flush()
            raise KeyboardInterrupt
        with self.db.session() as session:
            self.assertEqual(session.get(Employee, self.emp).first, "Acceptance")
        for index, invalid in [
            (0, "EMP1"),
            (3, "invalid"),
            (4, "12+34"),
            (5, "2026-02-30"),
            (6, "-1"),
            (7, "0.001"),
        ]:
            values = self.values.copy()
            values[index] = invalid
            with self.subTest(index=index), self.assertRaises(ValueError):
                self.service.save_employee(*values)

    def test_console_login_lists_updates_delete_logout_and_viewer(self):
        self.service.create_user(self.viewer, self.password)
        inputs = [
            "invalid",
            "1",
            self.username,
            "2",
            "3",
            "7",
            "11",
            "12",
            "8",
            *self.values,
            "10",
            self.rev,
            self.emp,
            "2026-10-31",
            "Good",
            "7",
            "9",
            self.emp,
            "CANCEL",
            "9",
            self.emp,
            "DELETE",
            "1",
            "1",
            self.viewer,
            "2",
            "3",
            "7",
            "1",
            "0",
        ]
        with (
            patch("builtins.input", side_effect=inputs),
            patch("ems.cli.password", return_value=self.password),
            patch("sys.stdout", new_callable=io.StringIO) as output,
        ):
            cli.run(Service(self.db), (SQLAlchemyError,))
        for message in (
            "Logged in",
            "Invalid choice",
            "Employee saved",
            "Review added",
            "Deletion cancelled",
            "Employee removed",
            "administrator access required",
        ):
            self.assertIn(message, output.getvalue())

    def test_short_launch_opens_correct_remote_database_and_exits(self):
        # Exercise real configuration, schema check, CLI startup and shutdown.
        with (
            patch("builtins.input", return_value="0"),
            patch("sys.stdout", new_callable=io.StringIO),
        ):
            argv = [] if self.environment == "preview" else ["production"]
            self.assertEqual(cli.main(argv), 0)


@unittest.skipUnless(
    os.environ.get("EMS_AZURE_TESTS") == "1", "Azure acceptance is opt-in"
)
class PreviewTests(AzureAcceptance, unittest.TestCase):
    environment = "preview"
    expected_database = "sql-emp-db-preview"
    expected_user = "ems_preview_app"


@unittest.skipUnless(
    os.environ.get("EMS_AZURE_TESTS") == "1", "Azure acceptance is opt-in"
)
class ProductionTests(AzureAcceptance, unittest.TestCase):
    environment = "production"
    expected_database = "sql-emp-db"
    expected_user = "ems_production_app"


if __name__ == "__main__":
    unittest.main()
