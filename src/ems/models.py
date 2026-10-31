"""SQLAlchemy mappings for the versioned SQL Server schema.

Production DDL remains in reviewed SQL migrations; importing models never creates tables.
Portable constraints also support ORM regression tests against isolated SQLite.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Computed,
    Date,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Department(Base):
    __tablename__ = "Departments"
    __table_args__ = {"schema": "dbo", "implicit_returning": False}

    department_id: Mapped[str] = mapped_column(
        "DepartmentID", String(10), primary_key=True
    )
    name: Mapped[str] = mapped_column("DepartmentName", String(100))
    location: Mapped[str] = mapped_column("DepartmentLocation", String(100))
    created: Mapped[date] = mapped_column("CreationDate", Date)


class Position(Base):
    __tablename__ = "Positions"
    __table_args__ = (
        UniqueConstraint("PositionID", "DepartmentID", name="EMS_PositionDepartment"),
        CheckConstraint(
            "MinSalary >= 0 AND MaxSalary >= MinSalary", name="EMS_SalaryRange"
        ),
        {"schema": "dbo", "implicit_returning": False},
    )

    position_id: Mapped[str] = mapped_column("PositionID", String(10), primary_key=True)
    title: Mapped[str] = mapped_column("PositionTitle", String(100))
    department_id: Mapped[str] = mapped_column(
        "DepartmentID", String(10), ForeignKey("dbo.Departments.DepartmentID")
    )
    minimum: Mapped[Decimal] = mapped_column("MinSalary", Numeric(12, 2))
    maximum: Mapped[Decimal] = mapped_column("MaxSalary", Numeric(12, 2))
    description: Mapped[str | None] = mapped_column("JobDescription", String(100))


class Employee(Base):
    __tablename__ = "Employees"
    __table_args__ = (
        ForeignKeyConstraint(
            ["PositionID", "DepartmentID"],
            ["dbo.Positions.PositionID", "dbo.Positions.DepartmentID"],
            name="EMS_EmployeePositionDepartment",
        ),
        CheckConstraint("BaseSalary >= 0 AND Bonus >= 0", name="EMS_Compensation"),
        {"schema": "dbo", "implicit_returning": False},
    )

    employee_id: Mapped[str] = mapped_column("EmployeeID", String(9), primary_key=True)
    first: Mapped[str] = mapped_column("FirstName", String(50))
    last: Mapped[str] = mapped_column("LastName", String(50))
    email: Mapped[str | None] = mapped_column("Email", String(100))
    phone: Mapped[str | None] = mapped_column("PhoneNumber", String(16))
    hired: Mapped[date] = mapped_column("HireDate", Date)
    salary: Mapped[Decimal] = mapped_column("BaseSalary", Numeric(12, 2))
    bonus: Mapped[Decimal] = mapped_column("Bonus", Numeric(12, 2))
    annual: Mapped[Decimal] = mapped_column(
        "AnnualCompensation", Numeric(24, 2), Computed("(BaseSalary + Bonus) * 12")
    )
    paid: Mapped[date] = mapped_column("PayDate", Date)
    department_id: Mapped[str] = mapped_column(
        "DepartmentID", String(10), ForeignKey("dbo.Departments.DepartmentID")
    )
    position_id: Mapped[str] = mapped_column(
        "PositionID", String(10), ForeignKey("dbo.Positions.PositionID")
    )


class PerformanceReview(Base):
    __tablename__ = "PerformanceReview"
    __table_args__ = (
        CheckConstraint("Rating BETWEEN 0 AND 9", name="EMS_Rating"),
        {"schema": "dbo", "implicit_returning": False},
    )

    review_id: Mapped[str] = mapped_column("ReviewID", String(9), primary_key=True)
    employee_id: Mapped[str] = mapped_column(
        "EmployeeID", String(9), ForeignKey("dbo.Employees.EmployeeID")
    )
    reviewed: Mapped[date] = mapped_column("ReviewDate", Date)
    comments: Mapped[str | None] = mapped_column("Comments", String(255))
    rating: Mapped[int] = mapped_column("Rating", Integer)


class Account(Base):
    __tablename__ = "Sign_Up"
    __table_args__ = (
        CheckConstraint("Role IN ('admin', 'viewer')", name="EMS_Role"),
        {"schema": "dbo", "implicit_returning": False},
    )

    username: Mapped[str] = mapped_column("Username", String(20), primary_key=True)
    password: Mapped[str] = mapped_column("Password", String(255))
    role: Mapped[str] = mapped_column("Role", String(10), default="viewer")


class SchemaVersion(Base):
    __tablename__ = "EMS_SchemaVersion"
    __table_args__ = {"schema": "dbo"}

    version: Mapped[int] = mapped_column("Version", Integer, primary_key=True)
