"""Exercise complete console journeys against real isolated ORM fixtures."""

import io
import unittest
from unittest.mock import patch

from sqlalchemy import select
from test_orm import EMPLOYEE, test_database

from ems.cli import main, new_password
from ems.models import Account, Employee, PerformanceReview, SchemaVersion
from ems.service import Service


class ConsoleJourneyTests(unittest.TestCase):
    def setUp(self):
        self.db = test_database()
        self.addCleanup(self.db.close)
        with self.db.session() as session:
            session.add(SchemaVersion(version=1))
        Service(self.db).bootstrap_admin("operator", "console password 123")

    def test_administrator_creates_all_records_and_account_then_viewer_logs_in(self):
        inputs = [
            "1",
            "operator",
            "4",
            "DEPT000001",
            "HR",
            "Town",
            "2024-01-01",
            "5",
            "POST000001",
            "Manager",
            "DEPT000001",
            "1",
            "100000",
            "Manage",
            "6",
            *EMPLOYEE,
            "2",
            "3",
            "7",
            "8",
            *EMPLOYEE,
            "10",
            "REV000001",
            "EMP000001",
            "2024-01-01",
            "Good",
            "7",
            "11",
            "12",
            "13",
            "reader",
            "viewer",
            "1",
            "1",
            "reader",
            "2",
            "3",
            "7",
            "1",
            "0",
        ]
        with (
            patch("ems.cli.Database.connect", return_value=self.db),
            patch.object(self.db, "close"),
            patch("ems.cli.password", return_value="console password 123"),
            patch("builtins.input", side_effect=inputs),
            patch("sys.stdout", new_callable=io.StringIO) as output,
        ):
            self.assertEqual(main([]), 0)
        for message in (
            "Department added",
            "Position added",
            "Employee saved",
            "Review added",
            "Account created",
            "AnnualCompensation: 601509.00",
            "administrator access required",
        ):
            self.assertIn(message, output.getvalue())
        with self.db.session() as session:
            self.assertIsNotNone(session.get(Employee, "EMP000001"))
            self.assertIsNotNone(session.get(PerformanceReview, "REV000001"))
            self.assertEqual(session.get(Account, "reader").role, "viewer")

    def test_empty_lists_invalid_input_and_delete_confirmation(self):
        svc = Service(self.db)
        self.assertTrue(svc.login("operator", "console password 123"))
        svc.add_department("DEPT000001", "HR", "Town", "2024-01-01")
        svc.add_position("POST000001", "Manager", "DEPT000001", "1", "100000", "")
        svc.save_employee(*EMPLOYEE)
        inputs = [
            "1",
            "operator",
            "11",
            "invalid",
            "9",
            "EMP000001",
            "no",
            "9",
            "EMP000001",
            "DELETE",
            "9",
            "EMP000001",
            "DELETE",
            "8",
            *EMPLOYEE,
            "7",
            "0",
        ]
        with (
            patch("ems.cli.Database.connect", return_value=self.db),
            patch.object(self.db, "close"),
            patch("ems.cli.password", return_value="console password 123"),
            patch("builtins.input", side_effect=inputs),
            patch("sys.stdout", new_callable=io.StringIO) as output,
        ):
            self.assertEqual(main(["production"]), 0)
        for message in (
            "No records found",
            "Invalid choice",
            "Deletion cancelled",
            "Employee removed",
            "Employee not found",
        ):
            self.assertIn(message, output.getvalue())
        with self.db.session() as session:
            self.assertEqual(list(session.scalars(select(Employee))), [])

    def test_password_confirmation_failure_creates_no_account(self):
        with (
            patch("ems.cli.password", side_effect=["long password 123", "different"]),
            self.assertRaises(ValueError),
        ):
            new_password()
        with self.db.session() as session:
            self.assertEqual(len(list(session.scalars(select(Account)))), 1)
