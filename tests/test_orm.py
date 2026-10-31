"""Real ORM/database regressions; SQLite is a test fixture, not a production backend."""

import hashlib
import unittest
from decimal import Decimal
from unittest.mock import patch

from sqlalchemy import create_engine, event, select
from sqlalchemy.dialects import mssql
from sqlalchemy.exc import IntegrityError

from ems.db import Database, DatabaseError
from ems.models import Account, Base, Employee, PerformanceReview, SchemaVersion
from ems.service import Service, User, locked

EMPLOYEE = (
    "EMP000001",
    "First",
    "Last",
    "first@example.com",
    "+923001234567",
    "2024-01-01",
    "50000.50",
    "125.25",
    "2024-01-31",
    "DEPT000001",
    "POST000001",
)


def test_database():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        execution_options={"schema_translate_map": {"dbo": None}},
        hide_parameters=True,
    )

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    return Database(engine)


class ORMTests(unittest.TestCase):
    def setUp(self):
        self.db = test_database()
        self.addCleanup(self.db.close)
        self.service = Service(self.db)
        self.service.user = User("operator", "admin")
        self.service.add_department("DEPT000001", "HR", "Town", "2024-01-01")
        self.service.add_position(
            "POST000001", "HR Manager", "DEPT000001", "100", "100000", "Manage HR"
        )

    def test_crud_decimal_phone_and_computed_compensation(self):
        values = list(EMPLOYEE)
        values[4] = "03001234567"
        self.assertTrue(self.service.save_employee(*values))
        with self.db.session() as session:
            record = session.get(Employee, "EMP000001")
            self.assertEqual(record.phone, "03001234567")
            self.assertEqual(record.salary, Decimal("50000.50"))
            self.assertEqual(record.annual, Decimal("601509.00"))
        values[1] = "Changed"
        self.assertTrue(self.service.save_employee(*values, update=True))
        self.assertTrue(self.service.remove_employee("EMP000001"))
        self.assertFalse(self.service.remove_employee("EMP000001"))
        self.assertFalse(self.service.save_employee(*EMPLOYEE, update=True))

    def test_injection_payload_is_data(self):
        values = list(EMPLOYEE)
        values[1] = "Robert'); DROP TABLE Employees;--"
        self.service.save_employee(*values)
        with self.db.session() as session:
            self.assertEqual(session.get(Employee, "EMP000001").first, values[1])
        self.assertEqual(len(self.service.list_records("employees")[1]), 1)

    def test_duplicate_and_department_mismatch_roll_back(self):
        self.service.save_employee(*EMPLOYEE)
        with self.assertRaises(IntegrityError):
            self.service.save_employee(*EMPLOYEE)
        self.service.add_department("DEPT000002", "Other", "Town", "2024-01-01")
        values = list(EMPLOYEE)
        values[9] = "DEPT000002"
        with self.assertRaises(IntegrityError):
            self.service.save_employee(*values, update=True)
        with self.db.session() as session:
            self.assertEqual(
                session.get(Employee, "EMP000001").department_id, "DEPT000001"
            )

    def test_employee_and_review_deletion_are_atomic(self):
        self.service.save_employee(*EMPLOYEE)
        self.service.add_review("REV000001", "EMP000001", "2024-01-01", "Good", "7")

        def fail_delete(session, context, instances):
            if any(isinstance(record, Employee) for record in session.deleted):
                raise RuntimeError("simulated employee delete failure")

        event.listen(self.db.sessions.class_, "before_flush", fail_delete)
        try:
            with self.assertRaises(RuntimeError):
                self.service.remove_employee("EMP000001")
        finally:
            event.remove(self.db.sessions.class_, "before_flush", fail_delete)
        with self.db.session() as session:
            self.assertIsNotNone(session.get(Employee, "EMP000001"))
            self.assertIsNotNone(session.get(PerformanceReview, "REV000001"))
        self.assertTrue(self.service.remove_employee("EMP000001"))
        self.assertEqual(self.service.list_records("reviews")[1], [])

    def test_interrupt_rolls_back_and_next_session_works(self):
        with self.assertRaises(KeyboardInterrupt):
            with self.db.session() as session:
                session.add(
                    Account(username="temporary", password="unused", role="viewer")
                )
                session.flush()
                raise KeyboardInterrupt
        with self.db.session() as session:
            self.assertIsNone(session.get(Account, "temporary"))

    def test_viewer_and_anonymous_cannot_mutate_or_read_sensitive_records(self):
        operations = [
            lambda: self.service.add_department(
                "DEPT000003", "HR", "Town", "2024-01-01"
            ),
            lambda: self.service.add_position(
                "POST000002", "HR", "DEPT000001", "1", "2", ""
            ),
            lambda: self.service.save_employee(*EMPLOYEE),
            lambda: self.service.remove_employee("EMP000001"),
            lambda: self.service.add_review(
                "REV000001", "EMP000001", "2024-01-01", "", "9"
            ),
            lambda: self.service.create_user("newuser", "long password 123"),
        ]
        for user in (None, User("reader", "viewer")):
            self.service.user = user
            with patch.object(
                self.db, "session", side_effect=AssertionError("unauthorized DB access")
            ):
                for operation in operations:
                    with self.assertRaises(PermissionError):
                        operation()
                for kind in ("employees", "reviews", "report"):
                    with self.assertRaises(PermissionError):
                        self.service.list_records(kind)
        self.service.user = User("reader", "viewer")
        self.assertNotIn("MinSalary", self.service.list_records("positions")[0])
        self.assertEqual(len(self.service.list_records("departments")[1]), 1)

    def test_report_outer_join_and_administrator_salary_ranges(self):
        self.service.save_employee(*EMPLOYEE)
        self.assertEqual(len(self.service.list_records("report")[1]), 1)
        self.service.add_review("REV000001", "EMP000001", "2024-01-01", "Good", "7")
        self.service.add_review("REV000002", "EMP000001", "2024-02-01", "Better", "8")
        self.assertEqual(len(self.service.list_records("report")[1]), 2)
        self.assertIn("MinSalary", self.service.list_records("positions")[0])

    def test_bootstrap_account_roles_and_legacy_rehash(self):
        self.service.user = None
        self.service.bootstrap_admin("operator", "secure password 123")
        with self.assertRaises(PermissionError):
            self.service.bootstrap_admin("another", "secure password 123")
        self.assertTrue(self.service.login("operator", "secure password 123"))
        self.service.create_user("reader", "reader password 123")
        self.assertTrue(self.service.login("reader", "reader password 123"))
        self.assertEqual(self.service.user.role, "viewer")
        old = hashlib.sha256(b"oldpass123").hexdigest()
        with self.db.session() as session:
            session.add(Account(username="legacy", password=old, role="viewer"))
        self.assertTrue(self.service.login("legacy", "oldpass123"))
        with self.db.session() as session:
            self.assertTrue(
                session.get(Account, "legacy").password.startswith(
                    "pbkdf2_sha256$600000$"
                )
            )
        self.assertFalse(self.service.login("unknown", "wrong"))
        self.assertIsNone(self.service.user)

    def test_failed_commit_does_not_authenticate_or_upgrade_hash(self):
        old = hashlib.sha256(b"oldpass123").hexdigest()
        with self.db.session() as session:
            session.add(Account(username="legacy", password=old, role="viewer"))

        def fail_commit(session):
            raise RuntimeError("simulated commit failure")

        event.listen(self.db.sessions.class_, "before_commit", fail_commit)
        try:
            with self.assertRaises(RuntimeError):
                self.service.login("legacy", "oldpass123")
        finally:
            event.remove(self.db.sessions.class_, "before_commit", fail_commit)
        self.assertIsNone(self.service.user)
        with self.db.session() as session:
            self.assertEqual(session.get(Account, "legacy").password, old)

    def test_invalid_salary_range_never_opens_a_session(self):
        with (
            patch.object(
                self.db, "session", side_effect=AssertionError("unexpected session")
            ),
            self.assertRaises(ValueError),
        ):
            self.service.add_position(
                "POST000002", "HR", "DEPT000001", "200", "100", ""
            )

    def test_schema_version_is_required(self):
        with self.assertRaises(DatabaseError):
            self.db.check_schema()
        with self.db.session() as session:
            session.add(SchemaVersion(version=1))
        self.db.check_schema()

    def test_mssql_lock_hints_compile_without_literal_user_input(self):
        statement = locked(
            select(Employee).where(Employee.employee_id == "EMP000001"), Employee
        )
        compiled = statement.compile(dialect=mssql.dialect())
        self.assertIn("WITH (UPDLOCK, HOLDLOCK)", str(compiled))
        self.assertNotIn("EMP000001", str(compiled))
        self.assertIn("EMP000001", compiled.params.values())

    def test_preview_changes_do_not_touch_another_database(self):
        production = test_database()
        self.addCleanup(production.close)
        with production.session() as session:
            session.add(Account(username="prod-only", password="unused", role="viewer"))
        self.service.save_employee(*EMPLOYEE)
        with production.session() as session:
            self.assertIsNone(session.get(Employee, "EMP000001"))
            self.assertIsNotNone(session.get(Account, "prod-only"))


if __name__ == "__main__":
    unittest.main()
