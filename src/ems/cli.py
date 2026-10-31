"""Console interface. Database access begins only after main() is invoked."""

import argparse
import getpass
import sys
import warnings

from sqlalchemy.exc import SQLAlchemyError

from .db import Database, DatabaseError
from .service import Service


def password(prompt="Password: "):
    # getpass otherwise warns and falls back to echoing input on redirected terminals.
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        try:
            return getpass.getpass(prompt)
        except getpass.GetPassWarning:
            raise ValueError(
                "Use an interactive terminal that supports hidden password input."
            ) from None


def new_password():
    value = password("New password (12–128 characters): ")
    if value != password("Confirm password: "):
        raise ValueError("Passwords do not match.")
    return value


def ask(*labels):
    return [input(label + ": ") for label in labels]


def show(service, kind):
    headers, rows = service.list_records(kind)
    if not rows:
        print("No records found.")
    for row in rows:
        for name, value in zip(headers, row):
            print(f"{name}: {value if value is not None else ''}")
        print()


def run(service, db_errors=()):
    failures = 0
    while True:
        try:
            if service.user is None:
                print("\nEmployee Management System\n0. Exit\n1. Log in")
                choice = input("Choice: ").strip()
                if choice == "0":
                    return
                if choice != "1":
                    print("Invalid choice. Enter 0 or 1.")
                    continue
                if service.login(input("Username: "), password()):
                    failures = 0
                    print(
                        f"Logged in as {service.user.username} ({service.user.role})."
                    )
                else:
                    failures += 1
                    print("Invalid username or password.")
                    if failures >= 5:
                        print("Too many failed attempts. Closing this session.")
                        return
                continue
            print("\n0. Exit\n1. Log out\n2. List departments\n3. List positions")
            admin = service.user.role == "admin"
            if admin:
                print(
                    "4. Add department\n5. Add position\n6. Add employee\n7. List employees\n8. Update employee\n9. Remove employee\n10. Add review\n11. List reviews\n12. Employee report\n13. Create account"
                )
            choice = input("Choice: ").strip()
            if choice == "0":
                return
            if choice == "1":
                service.user = None
            elif choice in ("2", "3"):
                show(service, {"2": "departments", "3": "positions"}[choice])
            elif not admin:
                print("Invalid choice or administrator access required.")
            elif choice in ("7", "11", "12"):
                show(
                    service, {"7": "employees", "11": "reviews", "12": "report"}[choice]
                )
            elif choice == "4":
                service.add_department(
                    *ask(
                        "Department ID",
                        "Name",
                        "Location",
                        "Creation date (YYYY-MM-DD)",
                    )
                )
                print("Department added.")
            elif choice == "5":
                service.add_position(
                    *ask(
                        "Position ID",
                        "Title",
                        "Department ID",
                        "Minimum monthly base salary",
                        "Maximum monthly base salary",
                        "Description (optional)",
                    )
                )
                print("Position added.")
            elif choice in ("6", "8"):
                values = ask(
                    "Employee ID",
                    "First name",
                    "Last name",
                    "Email (optional)",
                    "Phone (optional, + and 7–15 digits)",
                    "Hire date (YYYY-MM-DD)",
                    "Monthly base salary",
                    "Monthly recurring bonus",
                    "Pay date (YYYY-MM-DD)",
                    "Department ID",
                    "Position ID",
                )
                changed = service.save_employee(*values, update=choice == "8")
                print(
                    "Employee saved."
                    if changed
                    else "Employee not found; nothing changed."
                )
            elif choice == "9":
                employee_id = input("Employee ID: ")
                if (
                    input("Delete this employee and all their reviews? Type DELETE: ")
                    == "DELETE"
                ):
                    removed = service.remove_employee(employee_id)
                    print(
                        "Employee removed."
                        if removed
                        else "Employee not found; nothing changed."
                    )
                else:
                    print("Deletion cancelled.")
            elif choice == "10":
                service.add_review(
                    *ask(
                        "Review ID",
                        "Employee ID",
                        "Review date (YYYY-MM-DD)",
                        "Comments (optional)",
                        "Rating (0–9)",
                    )
                )
                print("Review added.")
            elif choice == "13":
                username = input("New username: ")
                role = input("Role (viewer/admin): ").strip().lower()
                service.create_user(username, new_password(), role)
                print("Account created.")
            else:
                print("Invalid choice.")
        except (ValueError, PermissionError) as exc:
            print(exc)
        except db_errors:
            print(
                "Database operation failed; changes were rolled back. Check for duplicate IDs, missing references, or invalid department/salary data. If the connection was lost, restart the application."
            )


def main(argv=None):
    parser = argparse.ArgumentParser(description="SQL Server employee administration")
    parser.add_argument(
        "environment",
        nargs="?",
        choices=("preview", "production"),
        help="Environment to launch (default: preview)",
    )
    parser.add_argument(
        "--env-file",
        help="Custom operator configuration; cannot be combined with an environment name",
    )
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument(
        "--init-db",
        action="store_true",
        help="Create the schema in an existing empty database",
    )
    actions.add_argument(
        "--migrate",
        action="store_true",
        help="Migrate the original coursework schema without deleting records",
    )
    actions.add_argument(
        "--seed-demo",
        action="store_true",
        help="Insert missing demo records; never overwrite existing records",
    )
    actions.add_argument(
        "--create-admin",
        action="store_true",
        help="Operator: provision the first administrator",
    )
    args = parser.parse_args(argv)
    if args.environment and args.env_file:
        parser.error("Choose an environment name or --env-file, not both.")
    env_file = args.env_file or f".env.{args.environment or 'preview'}"
    db = None
    try:
        db = Database.connect(env_file)
        import pyodbc

        service = Service(db)
        if args.init_db or args.migrate or args.seed_demo:
            name = (
                "001_schema.sql"
                if args.init_db
                else "002_migrate_legacy.sql"
                if args.migrate
                else "003_seed_demo.sql"
            )
            try:
                db.script(name)
            except pyodbc.Error as exc:
                # Setup messages come from our scripts, but never print connection strings.
                print(
                    "Database setup failed. No partial changes were committed.",
                    file=sys.stderr,
                )
                if "EMS:" in str(exc):
                    print(
                        str(exc).split("EMS:", 1)[1].split("(", 1)[0].strip(),
                        file=sys.stderr,
                    )
                return 1
            print("Database operation completed.")
        elif args.create_admin:
            db.check_schema()
            service.bootstrap_admin(
                input("First administrator username: "), new_password()
            )
            print("Administrator created. Restart without --create-admin to log in.")
        else:
            db.check_schema()
            run(service, (SQLAlchemyError,))
        return 0
    except (DatabaseError, ValueError, PermissionError) as exc:
        print(exc, file=sys.stderr)
        return 1
    except EOFError, KeyboardInterrupt:
        print("\nSession closed.")
        return 0
    except SQLAlchemyError:
        print(
            "Database operation failed; the transaction was rolled back. Check the connection and existing records.",
            file=sys.stderr,
        )
        return 1
    except Exception as exc:
        # ODBC diagnostics can contain sensitive data; do not dump a traceback to the console.
        if type(exc).__module__ == "pyodbc":
            print(
                "Database operation failed; no partial changes were committed.",
                file=sys.stderr,
            )
            return 1
        raise
    finally:
        if db is not None:
            db.close()
