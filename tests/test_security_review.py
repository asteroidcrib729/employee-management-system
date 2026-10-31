"""Regression tests for limited, on-demand security triage."""

import importlib
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
review = importlib.import_module("security_review")


class SecurityReviewTests(unittest.TestCase):
    def analyze(self, groups=(), events=(), **kwargs):
        return review.signals(
            groups,
            events,
            healthy=True,
            free_protected=True,
            storage_percent=1,
            **kwargs,
        )

    def group(self, table="Employees", operation="DELETE", count=5, role=None):
        return {
            "ObjectName": table,
            "Operation": operation,
            "Count": count,
            "SubjectRole": role,
        }

    def test_bulk_delete_threshold_and_ordinary_updates(self):
        self.assertEqual(
            self.analyze(
                [self.group(count=4), self.group(operation="UPDATE", count=100)]
            ),
            [],
        )
        self.assertEqual(
            self.analyze([self.group()]),
            [{"signal": "employee_bulk_deletion", "count": 5}],
        )

    def test_administrator_changes_and_schema_changes_require_review(self):
        result = self.analyze(
            [
                self.group("Sign_Up", "UPDATE", 1, "admin"),
                self.group("Employees", "ALTER_TABLE", 1),
            ]
        )
        self.assertEqual(
            {item["signal"] for item in result},
            {"administrator_account_changes", "schema_or_permission_changes"},
        )

    def test_login_failure_threshold_ignores_unrelated_connectivity(self):
        events = [
            {"event_subtype_desc": "login_failed_for_user", "event_count": 4},
            {"event_subtype_desc": "connection_terminated", "event_count": 100},
        ]
        self.assertEqual(self.analyze(events=events), [])
        events[0]["event_count"] = 5
        self.assertEqual(
            self.analyze(events=events),
            [{"signal": "repeated_sql_login_failures", "count": 5}],
        )

    def test_drift_free_limit_and_capacity_are_reported(self):
        result = review.signals(
            [], [], healthy=False, free_protected=False, storage_percent=80
        )
        self.assertEqual(len(result), 3)

    def test_inaccessible_logs_are_inconclusive_instead_of_clean(self):
        azure = MagicMock(production="fixture")
        azure.database.side_effect = lambda name: MagicMock(
            **{
                "engine.connect.side_effect": RuntimeError(
                    "private sensitive diagnostics"
                )
            }
        )
        result = review.review(azure, 24)
        self.assertEqual(result["exit_code"], 3)
        self.assertEqual(len(result["inconclusive"]), 3)
        self.assertNotIn("private sensitive", str(result))

    def test_triage_output_excludes_raw_identifiers_and_payloads(self):
        group = self.group()
        group.update(
            EntityId="private employee",
            DatabaseActor="private identity",
            Password="private hash",
        )
        self.assertNotIn("private", str(self.analyze([group])))
