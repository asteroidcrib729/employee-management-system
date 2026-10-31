"""Offline safety regressions for the local Azure operator tools."""

import importlib
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pyodbc

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
integration = importlib.import_module("test_azure_migrations")
verification = importlib.import_module("verify_azure_security")


class AzureOperatorSafetyTests(unittest.TestCase):
    def fixture(self, name):
        case = integration.AzureIntegrationTests(
            "test_fresh_schema_seed_crud_auth_and_constraints"
        )
        case.connections = []
        case.databases = [name]
        case.run_id = "this-run"
        case.azure = MagicMock(
            subscription="subscription", group="group", server="server"
        )
        case.created = [{"name": name, "deleted": False}]
        case.save_record = MagicMock()
        return case

    def test_cleanup_refuses_production_name_before_any_azure_call(self):
        case = self.fixture("sql-emp-db")
        with self.assertRaises(RuntimeError):
            case.cleanup_databases()
        case.azure.db.assert_not_called()

    def test_cleanup_refuses_wrong_resource_id_or_ownership_tag(self):
        name = "ems-test-" + "a" * 32
        valid_id = f"/subscriptions/subscription/resourceGroups/group/providers/Microsoft.Sql/servers/server/databases/{name}"
        for resource_id, owner in [
            (valid_id, "another-run"),
            (valid_id + "-other", "this-run"),
        ]:
            case = self.fixture(name)
            case.azure.db.side_effect = [
                [{"name": name}],
                {"id": resource_id, "tags": {"ems-integration-run": owner}},
            ]
            with self.subTest(owner=owner), self.assertRaises(RuntimeError):
                case.cleanup_databases()
            self.assertFalse(
                any(call.args[0] == "delete" for call in case.azure.db.call_args_list)
            )

    def test_owned_resource_deletion_requires_absence_verification(self):
        name = "ems-test-" + "b" * 32
        case = self.fixture(name)
        actual = {
            "id": f"/subscriptions/subscription/resourceGroups/group/providers/Microsoft.Sql/servers/server/databases/{name}",
            "tags": {"ems-integration-run": "this-run"},
        }
        case.azure.db.side_effect = [[{"name": name}], actual, None, []]
        case.cleanup_databases()
        self.assertTrue(case.created[0]["deleted"])
        case.save_record.assert_called_once()
        self.assertIn(
            unittest.mock.call("delete", "--name", name, "--yes"),
            case.azure.db.call_args_list,
        )

    def test_network_timeout_is_inconclusive_instead_of_authentication_denial(self):
        with (
            patch.object(
                verification.pyodbc,
                "connect",
                side_effect=pyodbc.Error("HYT00", "Timed out (0)"),
            ),
            patch.object(verification.time, "sleep"),
        ):
            result = verification.login_probe("nonfunctional fixture")
        self.assertIsNone(result["denied"])

    def test_authentication_and_certificate_denials_are_distinct(self):
        with patch.object(
            verification.pyodbc,
            "connect",
            side_effect=pyodbc.Error("28000", "Login failed (18456)"),
        ):
            self.assertTrue(verification.login_probe("nonfunctional fixture")["denied"])
        with patch.object(
            verification.pyodbc,
            "connect",
            side_effect=pyodbc.Error(
                "08001", "SSL Provider: target principal name is incorrect"
            ),
        ):
            result = verification.login_probe("nonfunctional fixture", certificate=True)
        self.assertTrue(result["denied"])

    def test_certificate_probe_removes_the_valid_server_hostname(self):
        with (
            patch.object(
                verification.socket,
                "getaddrinfo",
                return_value=[(2, 1, 6, "", ("192.0.2.10", 1433))],
            ),
            patch.object(
                verification, "login_probe", return_value={"denied": True}
            ) as probe,
        ):
            verification.certificate_hostname_probe(
                "DRIVER={fixture};SERVER=tcp:valid.example.com,1433;DATABASE=fixture;",
                "valid.example.com",
            )
        attempted = probe.call_args.args[0]
        self.assertNotIn("valid.example.com", attempted)
        self.assertIn("SERVER=tcp:192.0.2.10,1433;", attempted)
        self.assertIn("HostNameInCertificate=ems-security.invalid;", attempted)
