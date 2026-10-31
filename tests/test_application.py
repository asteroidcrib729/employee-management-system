"""Console, configuration, validation and password regressions."""

import getpass
import importlib
import io
import os
import tempfile
import unittest
import warnings
from pathlib import Path
from unittest.mock import MagicMock, patch

from ems import security
from ems import validation as v
from ems.cli import main, password, run
from ems.db import Database, DatabaseError, load_environment


class ValidationTests(unittest.TestCase):
    def test_decimal_amounts_and_phone_text_are_preserved(self):
        self.assertEqual(str(v.money("50000.50")), "50000.50")
        self.assertEqual(v.phone("03001234567"), "03001234567")
        self.assertEqual(v.phone("+923001234567"), "+923001234567")
        self.assertIsNone(v.phone(""))

    def test_invalid_amounts(self):
        for value in (
            "abc",
            "NaN",
            "Infinity",
            "-1",
            "0.001",
            "10000000000",
            "1e1000000",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                v.money(value)

    def test_dates_ids_emails_ratings_and_bounds(self):
        for function, value in [
            (v.day, "2024-02-30"),
            (v.day, "2024-1-01"),
            (v.email, "a@b"),
            (v.phone, "123+45678"),
            (v.rating, "10"),
            (v.rating, "1.0"),
            (v.username, "a b"),
        ]:
            with (
                self.subTest(function=function.__name__),
                self.assertRaises(ValueError),
            ):
                function(value)
        self.assertEqual(v.identifier("emp000001", "EMP"), "EMP000001")
        with self.assertRaises(ValueError):
            v.identifier("EMP1", "EMP")
        with self.assertRaises(ValueError):
            v.text("x" * 101, "Name", 100)


class SecurityTests(unittest.TestCase):
    def test_random_salt_and_password_verification(self):
        first = security.hash_password("same password 123")
        self.assertNotEqual(first, security.hash_password("same password 123"))
        self.assertEqual(
            security.verify_password("same password 123", first), (True, False)
        )
        self.assertEqual(
            security.verify_password("wrong password", first), (False, False)
        )

    def test_malformed_hashes_fail_closed_and_password_length_is_enforced(self):
        for stored in (
            None,
            "",
            "pbkdf2_sha256$9999999999$aa$bb",
            "a" * 63,
            "pbkdf2_sha256$x$aa$bb",
        ):
            self.assertEqual(security.verify_password("secret", stored), (False, False))
        for value in ("short", "x" * 129):
            with self.assertRaises(ValueError):
                security.hash_password(value)

    def test_hidden_password_input_never_falls_back_to_echo(self):
        def fallback(*args):
            warnings.warn("cannot hide", getpass.GetPassWarning)
            return "visible password"

        with (
            patch("getpass.getpass", side_effect=fallback),
            self.assertRaises(ValueError),
        ):
            password()


class ConsoleTests(unittest.TestCase):
    def test_text_menu_input_retries(self):
        service = MagicMock(user=None)
        with (
            patch("builtins.input", side_effect=["abc", "0"]),
            patch("sys.stdout", new_callable=io.StringIO) as output,
        ):
            run(service)
        self.assertIn("Invalid choice", output.getvalue())

    def test_database_failure_returns_to_menu(self):
        service = MagicMock()
        service.user.role = "admin"
        service.list_records.side_effect = RuntimeError("simulated failure")
        with (
            patch("builtins.input", side_effect=["2", "0"]),
            patch("sys.stdout", new_callable=io.StringIO) as output,
        ):
            run(service, (RuntimeError,))
        self.assertIn("rolled back", output.getvalue())

    def test_login_session_stops_after_five_failures(self):
        service = MagicMock(user=None)
        service.login.return_value = False
        with (
            patch(
                "builtins.input",
                side_effect=[x for _ in range(5) for x in ("1", "unknown")],
            ),
            patch("ems.cli.password", return_value="bad"),
            patch("sys.stdout", new_callable=io.StringIO) as output,
        ):
            run(service)
        self.assertIn("Too many failed attempts", output.getvalue())


class SetupTests(unittest.TestCase):
    def test_resume_retries_only_opening_and_closes_on_exhaustion(self):
        from sqlalchemy.exc import OperationalError

        resumed = OperationalError("SELECT DB_NAME()", None, Exception("(40613)"))
        for failures, succeeds in [(1, True), (4, False)]:
            db = MagicMock()
            context = MagicMock()
            context.__enter__.return_value.exec_driver_sql.return_value.scalar_one.return_value = "application"
            db.engine.connect.side_effect = [resumed] * failures + [context]
            with (
                self.subTest(failures=failures),
                patch(
                    "ems.db.load_environment",
                    return_value={"EMS_CONNECTION_STRING": "private"},
                ),
                patch.object(Database, "from_odbc", return_value=db),
                patch("ems.db.time.sleep") as sleep,
            ):
                if succeeds:
                    self.assertIs(Database.connect(), db)
                    db.close.assert_not_called()
                    sleep.assert_called_once_with(5)
                else:
                    with self.assertRaises(DatabaseError):
                        Database.connect()
                    self.assertEqual(sleep.call_count, 3)
                    db.close.assert_called_once()

    def test_authentication_errors_are_not_retried_and_diagnostics_are_hidden(self):
        from sqlalchemy.exc import OperationalError

        db = MagicMock()
        db.engine.connect.side_effect = OperationalError(
            "private SQL", None, Exception("private credential diagnostic (18456)")
        )
        with (
            patch(
                "ems.db.load_environment",
                return_value={"EMS_CONNECTION_STRING": "private"},
            ),
            patch.object(Database, "from_odbc", return_value=db),
            patch("ems.db.time.sleep") as sleep,
            self.assertRaises(DatabaseError) as error,
        ):
            Database.connect()
        self.assertNotIn("private", str(error.exception))
        sleep.assert_not_called()
        db.close.assert_called_once()

    def test_system_database_is_rejected_before_application_access(self):
        db = MagicMock()
        db.engine.connect.return_value.__enter__.return_value.exec_driver_sql.return_value.scalar_one.return_value = "master"
        with (
            patch(
                "ems.db.load_environment",
                return_value={"EMS_CONNECTION_STRING": "private"},
            ),
            patch.object(Database, "from_odbc", return_value=db),
            self.assertRaises(DatabaseError),
        ):
            Database.connect()
        db.close.assert_called_once()

    def test_administrative_failure_rolls_back_and_releases_resources(self):
        engine = MagicMock()
        connection = engine.raw_connection.return_value
        cursor = connection.cursor.return_value
        db = Database(engine)
        with self.assertRaises(KeyboardInterrupt):
            with db.raw_transaction():
                raise KeyboardInterrupt
        connection.rollback.assert_called_once()
        connection.commit.assert_not_called()
        cursor.close.assert_called_once()
        connection.close.assert_called_once()

    def test_cursor_cleanup_failure_still_releases_administrative_connection(self):
        engine = MagicMock()
        connection = engine.raw_connection.return_value
        connection.cursor.return_value.close.side_effect = RuntimeError(
            "cursor cleanup failed"
        )
        with self.assertRaises(RuntimeError):
            with Database(engine).raw_transaction():
                pass
        connection.close.assert_called_once()

    def test_only_known_administrative_scripts_are_allowed(self):
        engine = MagicMock()
        with self.assertRaises(ValueError):
            Database(engine).script("../../private.sql")
        engine.raw_connection.assert_not_called()

    def test_shutdown_closes_database_on_end_of_input(self):
        db = MagicMock()
        with (
            patch("ems.cli.Database.connect", return_value=db),
            patch("builtins.input", side_effect=EOFError),
            patch("sys.stdout", new_callable=io.StringIO),
        ):
            self.assertEqual(main(["--env-file", ".env.preview"]), 0)
        db.close.assert_called_once()

    def test_missing_configuration_has_no_traceback(self):
        with (
            patch(
                "ems.cli.Database.connect",
                side_effect=DatabaseError("Set EMS_CONNECTION_STRING"),
            ),
            patch("sys.stderr", new_callable=io.StringIO) as output,
        ):
            self.assertEqual(main([]), 1)
        self.assertIn("Set EMS_CONNECTION_STRING", output.getvalue())
        self.assertNotIn("Traceback", output.getvalue())

    def test_import_never_opens_a_database(self):
        with patch(
            "ems.db.Database.connect",
            side_effect=AssertionError("connection on import"),
        ):
            importlib.reload(importlib.import_module("ems.cli"))

    def test_environment_preserves_process_values_and_embedded_equals(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict(os.environ, {"EMS_EXISTING": "original"}),
        ):
            path = Path(directory) / ".env"
            path.write_text(
                "# Comment\nEMS_EXISTING=replaced\nEMS_NEW=abc=def;\n", encoding="utf-8"
            )
            values = load_environment(path)
            self.assertEqual(values["EMS_EXISTING"], "original")
            self.assertEqual(values["EMS_NEW"], "abc=def;")
            self.assertNotIn("EMS_NEW", os.environ)

    def test_environment_selection_never_leaks_between_launches(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict(os.environ, {}, clear=True),
        ):
            preview = Path(directory) / ".env.preview"
            production = Path(directory) / ".env.production"
            preview.write_text("EMS_CONNECTION_STRING=preview", encoding="utf-8")
            production.write_text("EMS_CONNECTION_STRING=production", encoding="utf-8")
            self.assertEqual(
                load_environment(preview)["EMS_CONNECTION_STRING"], "preview"
            )
            self.assertEqual(
                load_environment(production)["EMS_CONNECTION_STRING"], "production"
            )
            self.assertNotIn("EMS_CONNECTION_STRING", os.environ)

    def test_short_launches_and_operator_override_select_exact_files(self):
        for argv, expected in [
            ([], ".env.preview"),
            (["preview"], ".env.preview"),
            (["production"], ".env.production"),
            (["--env-file", ".env.operator"], ".env.operator"),
        ]:
            with (
                self.subTest(argv=argv),
                patch("ems.cli.Database.connect") as connect,
                patch("ems.cli.run"),
                patch("sys.stdout", new_callable=io.StringIO),
            ):
                self.assertEqual(main(argv), 0)
                connect.assert_called_once_with(expected)

    def test_conflicting_or_unknown_environment_never_connects(self):
        for argv in (["production", "--env-file", ".env.preview"], ["prodution"]):
            with (
                self.subTest(argv=argv),
                patch("ems.cli.Database.connect") as connect,
                patch("sys.stderr", new_callable=io.StringIO),
                self.assertRaises(SystemExit),
            ):
                main(argv)
            connect.assert_not_called()

    def test_explicit_missing_environment_file_fails_closed(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            self.assertRaises(DatabaseError),
        ):
            load_environment(Path(directory) / ".env.preview")

    def test_azure_engine_releases_idle_connections_and_hides_parameters(self):
        import pyodbc
        from sqlalchemy.pool import NullPool

        db = Database.from_odbc(
            "DRIVER={ODBC Driver 18 for SQL Server};SERVER=example.database.windows.net;DATABASE=ems-preview;UID=example;PWD={secret;=value};Encrypt=yes;TrustServerCertificate=no;"
        )
        self.addCleanup(db.close)
        self.assertIsInstance(db.engine.pool, NullPool)
        self.assertTrue(db.engine.hide_parameters)
        self.assertFalse(pyodbc.pooling)
        self.assertIn("PWD={secret;=value}", db.engine.url.query["odbc_connect"])


if __name__ == "__main__":
    unittest.main()
