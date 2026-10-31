"""ORM sessions for application data; a bounded DBAPI path for reviewed migrations."""

import os
import time
from contextlib import contextmanager
from importlib.resources import files
from pathlib import Path

from sqlalchemy import URL, create_engine, inspect
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from .models import SchemaVersion


class DatabaseError(Exception):
    pass


def load_environment(path=".env.preview"):
    """Read one configuration without leaking it into later launches in this process."""
    values = {}
    path = Path(path)
    if path.exists():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                name, value = line.split("=", 1)
                values[name.strip()] = value.strip().strip('"').strip("'")
    else:
        raise DatabaseError(f"Environment file does not exist: {path}")
    return values | dict(os.environ)


class Database:
    def __init__(self, engine):
        self.engine = engine
        self.sessions = sessionmaker(bind=engine, expire_on_commit=False)

    @classmethod
    def from_odbc(cls, value):
        import pyodbc

        # Both layers must release idle connections so Azure serverless can pause.
        pyodbc.pooling = False
        url = URL.create("mssql+pyodbc", query={"odbc_connect": value})
        return cls(
            create_engine(
                url,
                poolclass=NullPool,
                hide_parameters=True,
                connect_args={"timeout": 30},
            )
        )

    @classmethod
    def connect(cls, env_file=".env.preview"):
        values = load_environment(env_file)
        value = values.get("EMS_CONNECTION_STRING", "").strip()
        if not value:
            raise DatabaseError(
                f"Set EMS_CONNECTION_STRING in {env_file}; see .env.example."
            )
        db = None
        try:
            db = cls.from_odbc(value)
            for attempt in range(4):
                try:
                    with db.engine.connect() as connection:
                        current = connection.exec_driver_sql(
                            "SELECT DB_NAME()"
                        ).scalar_one()
                        if current.lower() in ("master", "model", "msdb", "tempdb"):
                            raise DatabaseError(
                                "Choose an application database; system databases are not supported."
                            )
                    break
                except SQLAlchemyError as exc:
                    # Retry only opening a paused database, never an application write.
                    if "(40613)" not in str(getattr(exc, "orig", "")) or attempt == 3:
                        raise
                    time.sleep(5 * (attempt + 1))
            return db
        except (SQLAlchemyError, DatabaseError) as exc:
            if db is not None:
                db.close()
            if isinstance(exc, DatabaseError):
                raise
            raise DatabaseError(
                "Cannot connect to SQL Server. Check the driver, server, database, credentials and TLS settings."
            ) from None

    @contextmanager
    def session(self):
        with self.sessions.begin() as session:
            if self.engine.dialect.name == "mssql":
                session.connection().exec_driver_sql(
                    "SET XACT_ABORT ON; SET NOCOUNT OFF;"
                )
            yield session

    def check_schema(self):
        schema = "dbo" if self.engine.dialect.name == "mssql" else None
        with self.engine.connect() as connection:
            exists = inspect(connection).has_table("EMS_SchemaVersion", schema=schema)
        if exists:
            with self.session() as session:
                if session.get(SchemaVersion, 1) is not None:
                    return
        raise DatabaseError(
            "Initialize the empty database with --init-db, or back up and migrate the original schema with --migrate."
        )

    @contextmanager
    def raw_transaction(self):
        """Administrative SQL only. Never interpolate console inputs into this path."""
        connection = self.engine.raw_connection()
        cursor = None
        try:
            cursor = connection.cursor()
            cursor.execute("SET XACT_ABORT ON; SET NOCOUNT OFF;")
            yield cursor
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            try:
                if cursor is not None:
                    cursor.close()
            finally:
                connection.close()

    def script(self, name):
        if name not in (
            "001_schema.sql",
            "002_migrate_legacy.sql",
            "003_seed_demo.sql",
            "004_change_journal.sql",
        ):
            raise ValueError("Unknown database setup script.")
        sql = files("ems.sql").joinpath(name).read_text(encoding="utf-8")
        with self.raw_transaction() as cursor:
            cursor.execute(sql)
            while cursor.nextset():
                pass

    def close(self):
        self.engine.dispose()
