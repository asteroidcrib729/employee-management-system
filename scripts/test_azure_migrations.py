"""Run the existing two integration contracts in temporary free Azure databases.

Explicit local operator command. Creates at most two UUID-named databases, verifies
free-limit protection and deletes only resources tagged with this run's identity.
"""

import argparse
import json
import re
import sys
import unittest
import uuid

import pyodbc
from azure_sql import ROOT, AzureSql

sys.path.insert(0, str(ROOT / "tests"))
from test_sql_server import SqlServerTests  # noqa: E402


class AzureIntegrationTests(SqlServerTests):
    __unittest_skip__ = False

    @classmethod
    def setUpClass(cls):
        cls.azure = AzureSql()
        cls.run_id = uuid.uuid4().hex
        cls.created = []
        cls.record = ROOT / ".local/azure/integration-run.json"
        cls.record.parent.mkdir(parents=True, exist_ok=True)
        cls.record.write_text(
            json.dumps({"run_id": cls.run_id, "resources": []}), encoding="utf-8"
        )
        inventory = cls.azure.db("list")
        if len([db for db in inventory if db["name"] != "master"]) > 8:
            raise RuntimeError("Insufficient free-database slots for two bounded tests")

    def setUp(self):
        self.pyodbc = pyodbc
        self.connections = []
        self.databases = []
        self.addCleanup(self.cleanup_databases)

    def database(self):
        name = "ems-test-" + uuid.uuid4().hex
        if name in {db["name"] for db in self.azure.db("list")}:
            raise RuntimeError("Refusing to reuse an existing database")
        self.databases.append(name)
        self.created.append({"name": name, "deleted": False})
        self.save_record()
        print(f"Creating temporary free integration database: {name}", flush=True)
        self.azure.db(
            "create",
            "--name",
            name,
            "--edition",
            "GeneralPurpose",
            "--family",
            "Gen5",
            "--capacity",
            "2",
            "--min-capacity",
            "0.5",
            "--compute-model",
            "Serverless",
            "--max-size",
            "32GB",
            "--backup-storage-redundancy",
            "Local",
            "--use-free-limit",
            "true",
            "--free-limit-exhaustion-behavior",
            "AutoPause",
            "--tags",
            f"ems-integration-run={self.run_id}",
            "purpose=temporary-integration",
        )
        actual = self.azure.db("show", "--name", name)
        if (
            actual.get("useFreeLimit") is not True
            or actual.get("freeLimitExhaustionBehavior") != "AutoPause"
        ):
            raise RuntimeError(
                "Free-limit protection not confirmed; refusing test workload"
            )
        db = self.azure.database(name)
        self.connections.append(db)
        with db.engine.connect() as connection:
            if (
                connection.exec_driver_sql(
                    "SELECT COUNT(*) FROM sys.tables WHERE is_ms_shipped=0"
                ).scalar_one()
                != 0
            ):
                raise RuntimeError("Temporary database is not empty")
        return db

    @classmethod
    def save_record(cls):
        cls.record.write_text(
            json.dumps({"run_id": cls.run_id, "resources": cls.created}, indent=2),
            encoding="utf-8",
        )

    def cleanup_databases(self):
        for db in self.connections:
            db.close()
        for name in self.databases:
            if not re.fullmatch(r"ems-test-[0-9a-f]{32}", name):
                raise RuntimeError("Refusing to delete an unowned database name")
            inventory = {db["name"]: db for db in self.azure.db("list")}
            if name in inventory:
                actual = self.azure.db("show", "--name", name)
                expected_id = f"/subscriptions/{self.azure.subscription}/resourceGroups/{self.azure.group}/providers/Microsoft.Sql/servers/{self.azure.server}/databases/{name}"
                if (
                    actual["id"].lower() != expected_id.lower()
                    or actual.get("tags", {}).get("ems-integration-run") != self.run_id
                ):
                    raise RuntimeError(
                        "Ownership check failed; refusing resource deletion"
                    )
                self.azure.db("delete", "--name", name, "--yes")
            if name in {db["name"] for db in self.azure.db("list")}:
                raise RuntimeError("Temporary database cleanup could not be verified")
            next(item for item in self.created if item["name"] == name)["deleted"] = (
                True
            )
            self.save_record()
            print(f"Verified deletion of temporary database: {name}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test", choices=("all", "fresh", "migration"), default="all")
    choice = parser.parse_args().test
    if choice == "all":
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(AzureIntegrationTests)
    else:
        name = (
            "test_fresh_schema_seed_crud_auth_and_constraints"
            if choice == "fresh"
            else "test_legacy_migration_is_atomic_preserves_data_and_upgrades_login"
        )
        suite = unittest.TestSuite([AzureIntegrationTests(name)])
    outcome = unittest.TextTestRunner(verbosity=2, stream=sys.stdout).run(suite)
    raise SystemExit(not outcome.wasSuccessful())
