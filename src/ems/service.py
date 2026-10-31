"""Validated, authorized SQLAlchemy ORM operations."""

from dataclasses import dataclass
from functools import wraps

from sqlalchemy import and_, delete, select

from . import security
from . import validation as v
from .models import Account, Department, Employee, PerformanceReview, Position


@dataclass(frozen=True)
class User:
    username: str
    role: str


def administrator(method):
    @wraps(method)
    def checked(self, *args, **kwargs):
        if self.user is None or self.user.role != "admin":
            raise PermissionError("Administrator access required.")
        return method(self, *args, **kwargs)

    return checked


def locked(statement, model):
    """SQL Server range/update locks protect bootstrap and competing employee edits."""
    return statement.with_hint(model, "WITH (UPDLOCK, HOLDLOCK)", dialect_name="mssql")


class Service:
    def __init__(self, db):
        self.db = db
        self.user = None

    def login(self, username, password):
        self.user = None
        username = v.username(username)
        with self.db.session() as session:
            account = session.scalar(
                select(Account).where(Account.username == username)
            )
            valid, upgrade = security.verify_password(
                password, account.password if account else None
            )
            if not valid or account.role not in ("admin", "viewer"):
                return False
            if upgrade:
                account.password = security.upgrade_password(password)
            role = account.role
        self.user = User(username, role)
        return True

    @administrator
    def create_user(self, username, password, role="viewer"):
        username = v.username(username)
        if role not in ("admin", "viewer"):
            raise ValueError("Role must be admin or viewer.")
        encoded = security.hash_password(password)
        with self.db.session() as session:
            session.add(Account(username=username, password=encoded, role=role))

    def bootstrap_admin(self, username, password):
        """Operator-only first-admin setup, serialized by SQL Server range locks."""
        username = v.username(username)
        encoded = security.hash_password(password)
        with self.db.session() as session:
            statement = locked(select(Account).where(Account.role == "admin"), Account)
            if session.scalar(statement) is not None:
                raise PermissionError(
                    "An administrator already exists. Log in to create additional accounts."
                )
            session.add(Account(username=username, password=encoded, role="admin"))

    @administrator
    def add_department(self, department_id, name, location, created):
        record = Department(
            department_id=v.identifier(department_id, "DEPT"),
            name=v.text(name, "Name", 100),
            location=v.text(location, "Location", 100),
            created=v.day(created),
        )
        with self.db.session() as session:
            session.add(record)

    @administrator
    def add_position(
        self, position_id, title, department_id, minimum, maximum, description
    ):
        minimum, maximum = v.money(minimum), v.money(maximum)
        if minimum > maximum:
            raise ValueError("Minimum salary cannot exceed maximum salary.")
        record = Position(
            position_id=v.identifier(position_id, "POST"),
            title=v.text(title, "Title", 100),
            department_id=v.identifier(department_id, "DEPT"),
            minimum=minimum,
            maximum=maximum,
            description=v.text(description, "Description", 100, True),
        )
        with self.db.session() as session:
            session.add(record)

    @administrator
    def save_employee(
        self,
        employee_id,
        first,
        last,
        email,
        phone,
        hired,
        salary,
        bonus,
        paid,
        department_id,
        position_id,
        *,
        update=False,
    ):
        employee_id = v.identifier(employee_id, "EMP")
        values = dict(
            first=v.text(first, "First name", 50),
            last=v.text(last, "Last name", 50),
            email=v.email(email),
            phone=v.phone(phone),
            hired=v.day(hired),
            salary=v.money(salary),
            bonus=v.money(bonus),
            paid=v.day(paid),
            department_id=v.identifier(department_id, "DEPT"),
            position_id=v.identifier(position_id, "POST"),
        )
        with self.db.session() as session:
            if update:
                record = session.scalar(
                    locked(
                        select(Employee).where(Employee.employee_id == employee_id),
                        Employee,
                    )
                )
                if record is None:
                    return False
                for name, value in values.items():
                    setattr(record, name, value)
            else:
                session.add(Employee(employee_id=employee_id, **values))
        return True

    @administrator
    def remove_employee(self, employee_id):
        employee_id = v.identifier(employee_id, "EMP")
        with self.db.session() as session:
            record = session.scalar(
                locked(
                    select(Employee).where(Employee.employee_id == employee_id),
                    Employee,
                )
            )
            if record is None:
                return False
            session.execute(
                delete(PerformanceReview).where(
                    PerformanceReview.employee_id == employee_id
                )
            )
            session.delete(record)
        return True

    @administrator
    def add_review(self, review_id, employee_id, reviewed, comments, rating):
        record = PerformanceReview(
            review_id=v.identifier(review_id, "REV"),
            employee_id=v.identifier(employee_id, "EMP"),
            reviewed=v.day(reviewed),
            comments=v.text(comments, "Comments", 255, True),
            rating=v.rating(rating),
        )
        with self.db.session() as session:
            session.add(record)

    def list_records(self, kind):
        if self.user is None:
            raise PermissionError("Log in first.")
        columns = {
            "departments": [
                Department.department_id,
                Department.name,
                Department.location,
                Department.created,
            ],
            "positions": [
                Position.position_id,
                Position.title,
                Position.department_id,
                Position.description,
            ],
            "employees": [
                Employee.employee_id,
                Employee.first,
                Employee.last,
                Employee.email,
                Employee.phone,
                Employee.hired,
                Employee.salary,
                Employee.bonus,
                Employee.annual,
                Employee.paid,
                Employee.department_id,
                Employee.position_id,
            ],
            "reviews": [
                PerformanceReview.review_id,
                PerformanceReview.employee_id,
                PerformanceReview.reviewed,
                PerformanceReview.comments,
                PerformanceReview.rating,
            ],
            "report": [
                Employee.employee_id,
                Employee.first,
                Employee.last,
                Department.name,
                Position.title,
                Employee.salary,
                Employee.bonus,
                Employee.annual,
                PerformanceReview.review_id,
                PerformanceReview.reviewed,
                PerformanceReview.comments,
                PerformanceReview.rating,
            ],
        }
        if kind not in columns:
            raise ValueError("Unknown record type.")
        if kind not in ("departments", "positions") and self.user.role != "admin":
            raise PermissionError(
                "Administrator access required for employee, compensation and review data."
            )
        if kind == "positions" and self.user.role == "admin":
            columns[kind] = [
                Position.position_id,
                Position.title,
                Position.department_id,
                Position.minimum,
                Position.maximum,
                Position.description,
            ]
        fields = columns[kind]
        statement = select(
            *(field.label(field.property.columns[0].name) for field in fields)
        )
        if kind == "report":
            statement = (
                statement.select_from(Employee)
                .join(Department, Employee.department_id == Department.department_id)
                .join(
                    Position,
                    and_(
                        Employee.position_id == Position.position_id,
                        Employee.department_id == Position.department_id,
                    ),
                )
                .outerjoin(
                    PerformanceReview,
                    Employee.employee_id == PerformanceReview.employee_id,
                )
                .order_by(Employee.employee_id, PerformanceReview.review_id)
            )
        else:
            statement = statement.order_by(fields[0])
        with self.db.session() as session:
            result = session.execute(statement)
            return list(result.keys()), result.all()
