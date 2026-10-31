"""Opt-in SQL Server tests; every database name is generated and owned by this suite."""

import hashlib
import os
import re
import unittest
import uuid
import zipfile
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import NullPool
from test_orm import EMPLOYEE

from ems.db import Database
from ems.service import Service, User


@unittest.skipUnless(
    os.environ.get("EMS_TEST_SERVER_CONNECTION"),
    "SQL Server integration connection not configured",
)
class SqlServerTests(unittest.TestCase):
    def setUp(self):
        import pyodbc

        self.pyodbc = pyodbc
        pyodbc.pooling = False
        self.master = pyodbc.connect(
            os.environ["EMS_TEST_SERVER_CONNECTION"], autocommit=True, timeout=15
        )
        self.databases = []
        self.connections = []
        self.addCleanup(self.cleanup_databases)

    def cleanup_databases(self):
        for db in self.connections:
            db.close()
        for name in self.databases:
            if not re.fullmatch(r"ems_test_[0-9a-f]{32}", name):
                raise AssertionError("Refusing to clean up an unowned database")
            cursor = self.master.cursor()
            try:
                cursor.execute(
                    f"ALTER DATABASE [{name}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE"
                )
                cursor.execute(f"DROP DATABASE [{name}]")
            finally:
                cursor.close()
        self.master.close()

    def database(self):
        name = "ems_test_" + uuid.uuid4().hex
        cursor = self.master.cursor()
        try:
            cursor.execute(f"CREATE DATABASE [{name}]")
            self.databases.append(name)
        finally:
            cursor.close()

        def connection_factory():
            connection = self.pyodbc.connect(
                os.environ["EMS_TEST_SERVER_CONNECTION"], autocommit=True, timeout=15
            )
            cursor = connection.cursor()
            try:
                cursor.execute(f"USE [{name}]")
            finally:
                cursor.close()
            connection.autocommit = False
            return connection

        db = Database(
            create_engine(
                "mssql+pyodbc://",
                creator=connection_factory,
                poolclass=NullPool,
                hide_parameters=True,
            )
        )
        self.connections.append(db)
        return db

    def test_fresh_schema_seed_crud_auth_and_constraints(self):
        db = self.database()
        db.script("001_schema.sql")
        db.script("001_schema.sql")
        db.script("003_seed_demo.sql")
        db.script("003_seed_demo.sql")
        with db.raw_transaction() as c:
            c.execute("SELECT COUNT(*) FROM dbo.Employees")
            self.assertEqual(c.fetchone()[0], 20)
            c.execute(
                "SELECT DepartmentID FROM dbo.Employees WHERE EmployeeID='EMP000005'"
            )
            self.assertEqual(c.fetchone()[0], "DEPT000005")
            c.execute(
                "UPDATE dbo.Employees SET FirstName='Retained' WHERE EmployeeID='EMP000001'"
            )
        db.script("003_seed_demo.sql")
        with db.raw_transaction() as c:
            c.execute(
                "SELECT FirstName FROM dbo.Employees WHERE EmployeeID='EMP000001'"
            )
            self.assertEqual(c.fetchone()[0], "Retained")
        service = Service(db)
        service.bootstrap_admin("operator", "a secure password 123")
        self.assertTrue(service.login("operator", "a secure password 123"))
        with self.assertRaises(PermissionError):
            Service(db).bootstrap_admin("other", "a secure password 123")
        values = list(EMPLOYEE)
        values[0] = "EMP999999"
        values[4] = "03001234567"
        service.save_employee(*values)
        with db.raw_transaction() as c:
            c.execute(
                "SELECT PhoneNumber, BaseSalary, AnnualCompensation FROM dbo.Employees WHERE EmployeeID=?",
                (values[0],),
            )
            row = c.fetchone()
            self.assertEqual(row[0], "03001234567")
            self.assertEqual(str(row[1]), "50000.50")
            self.assertEqual(row[2], (row[1] + Decimal("125.25")) * 12)
        self.assertTrue(service.save_employee(*values, update=True))
        values[9] = "DEPT000002"
        with self.assertRaises(IntegrityError):
            service.save_employee(*values, update=True)
        self.assertTrue(service.remove_employee("EMP999999"))
        self.assertFalse(service.remove_employee("EMP999999"))
        self.assertFalse(service.save_employee("EMP999999", *EMPLOYEE[1:], update=True))
        with self.assertRaises(self.pyodbc.IntegrityError):
            with db.raw_transaction() as c:
                c.execute(
                    "UPDATE dbo.Positions SET MinSalary=-1 WHERE PositionID='POST000001'"
                )
        with self.assertRaises(self.pyodbc.IntegrityError):
            with db.raw_transaction() as c:
                c.execute(
                    "UPDATE dbo.Employees SET Bonus=-1 WHERE EmployeeID='EMP000001'"
                )
        with self.assertRaises(self.pyodbc.IntegrityError):
            with db.raw_transaction() as c:
                c.execute(
                    "UPDATE dbo.PerformanceReview SET Rating=10 WHERE ReviewID='REV000001'"
                )
        self.assertEqual(len(service.list_records("report")[1]), 20)
        service.create_user("reader", "a reader password 123")
        self.assertTrue(service.login("reader", "a reader password 123"))
        with self.assertRaises(PermissionError):
            service.list_records("employees")
        self.assertEqual(len(service.list_records("departments")[1]), 20)

    def test_legacy_migration_is_atomic_preserves_data_and_upgrades_login(self):
        db = self.database()
        archive = (
            Path(__file__).resolve().parents[1]
            / "development-plans"
            / "legacy"
            / "original-source.zip"
        )
        with zipfile.ZipFile(archive) as z:
            sql = z.read(
                "DBMS - Employee Management System/Employee Management System - SQL.sql"
            ).decode()
        batches = re.split(r"^GO\s*$", sql, flags=re.M)
        # Skip CREATE DATABASE and USE; all legacy DDL/seed executes only in our generated database.
        for batch in batches[2:12]:
            # Original checks qualified a fixed database name. Use the current test database instead.
            batch = batch.replace("EmployeeManagementDB.SYS.", "SYS.")
            with db.raw_transaction() as c:
                c.execute(batch)
                while c.nextset():
                    pass
        old = hashlib.sha256(b"oldpass123").hexdigest()
        with db.raw_transaction() as c:
            c.execute("INSERT INTO dbo.Sign_Up VALUES (?,?)", ("legacy", old))
        with self.assertRaises(self.pyodbc.Error) as mismatch:
            db.script("002_migrate_legacy.sql")
        self.assertIn(
            "Employee and position departments disagree", str(mismatch.exception)
        )
        with db.raw_transaction() as c:
            c.execute("SELECT COUNT(*) FROM dbo.Employees")
            self.assertEqual(c.fetchone()[0], 20)
            c.execute("SELECT COL_LENGTH('dbo.Sign_Up','Role')")
            self.assertIsNone(c.fetchone()[0])
            # Deliberate correction of known sample data, only in this disposable database.
            c.execute(
                "UPDATE dbo.Employees SET DepartmentID='DEPT000005' WHERE EmployeeID='EMP000005'"
            )
            # This passes the old schema but fails the new name constraint after DDL.
            c.execute(
                "UPDATE dbo.Employees SET FirstName='' WHERE EmployeeID='EMP000001'"
            )
        with self.assertRaises(self.pyodbc.Error) as invalid_name:
            db.script("002_migrate_legacy.sql")
        self.assertIn("EMS_EmployeeNames", str(invalid_name.exception))
        with db.raw_transaction() as c:
            c.execute("SELECT COL_LENGTH('dbo.Sign_Up','Role')")
            self.assertIsNone(c.fetchone()[0])
            c.execute(
                "SELECT TYPE_NAME(user_type_id) FROM sys.columns WHERE object_id=OBJECT_ID('dbo.Employees') AND name='PhoneNumber'"
            )
            self.assertEqual(c.fetchone()[0], "bigint")
            c.execute(
                "UPDATE dbo.Employees SET FirstName='John' WHERE EmployeeID='EMP000001'"
            )
        db.script("002_migrate_legacy.sql")
        db.script("002_migrate_legacy.sql")
        service = Service(db)
        self.assertTrue(service.login("legacy", "oldpass123"))
        self.assertEqual(service.user, User("legacy", "viewer"))
        with db.raw_transaction() as c:
            c.execute("SELECT Password FROM dbo.Sign_Up WHERE Username='legacy'")
            self.assertTrue(c.fetchone()[0].startswith("pbkdf2_sha256$"))
            c.execute("SELECT COUNT(*) FROM dbo.PerformanceReview")
            self.assertEqual(c.fetchone()[0], 20)


if __name__ == "__main__":
    unittest.main()
