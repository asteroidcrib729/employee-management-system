"""Local Azure SQL operator helpers. Never log access tokens or connection strings."""

import json
import shutil
import struct
import subprocess
import time
from pathlib import Path

import pyodbc
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from ems.db import Database

ROOT = Path(__file__).resolve().parents[1]


class AzureSql:
    def __init__(self):
        values = json.loads((ROOT / ".local/template/parameters.json").read_text())[
            "parameters"
        ]
        self.subscription = values["subscriptionId"]["value"]
        self.group = values["resourceGroupName"]["value"]
        self.server = values["serverName"]["value"]
        self.production = values["databaseName"]["value"]
        self.cli = (
            shutil.which("az")
            or r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
        )
        self.scope = [
            "--subscription",
            self.subscription,
            "--resource-group",
            self.group,
        ]
        self.token = None
        pyodbc.pooling = False

    def run(self, *args):
        result = subprocess.run(
            [self.cli, *args, "--only-show-errors", "--output", "json"],
            capture_output=True,
            text=True,
            timeout=480,
            check=False,
        )
        if result.returncode:
            raise RuntimeError(f"Azure command failed: {' '.join(args[:3])}")
        return json.loads(result.stdout) if result.stdout.strip() else None

    def db(self, *args):
        return self.run("sql", "db", *args, *self.scope, "--server", self.server)

    def connection(self, database):
        if self.token is None:
            result = self.run(
                "account",
                "get-access-token",
                "--subscription",
                self.subscription,
                "--resource",
                "https://database.windows.net/",
            )
            token = result["accessToken"].encode("utf-16-le")
            self.token = struct.pack("<I", len(token)) + token
        for attempt in range(5):
            try:
                return pyodbc.connect(
                    "DRIVER={ODBC Driver 18 for SQL Server};"
                    f"SERVER=tcp:{self.server}.database.windows.net,1433;DATABASE={database};"
                    "Encrypt=yes;TrustServerCertificate=no;",
                    attrs_before={1256: self.token},
                    timeout=30,
                )
            except pyodbc.Error as exc:
                if "(40613)" not in str(exc) or attempt == 4:
                    raise RuntimeError("Azure SQL operator connection failed") from None
                time.sleep(5)

    def database(self, name):
        return Database(
            create_engine(
                "mssql+pyodbc://",
                creator=lambda: self.connection(name),
                poolclass=NullPool,
                hide_parameters=True,
            )
        )
