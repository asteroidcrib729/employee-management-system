"""Inspect the wheel and sdist for required files and accidental local data."""

import email
import tarfile
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]


def check_names(names):
    for name in names:
        parts = PurePosixPath(name).parts
        assert not {".local", ".venv", ".uv-cache", ".git", "__pycache__"}.intersection(
            parts
        )
        assert not any(p.startswith(".env") and p != ".env.example" for p in parts)


def main():
    wheel = ROOT / "dist/employee_management_system-1.0.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        check_names(names)
        for script in (
            "000_preflight_legacy",
            "001_schema",
            "002_migrate_legacy",
            "003_seed_demo",
            "004_change_journal",
        ):
            assert f"ems/sql/{script}.sql" in names
        info = next(name for name in names if name.endswith(".dist-info/METADATA"))
        metadata = email.message_from_bytes(archive.read(info))
        assert metadata["Requires-Python"] == "==3.14.7"
        assert metadata["License-Expression"] == "Apache-2.0"
        assert set(metadata.get_all("License-File")) == {"LICENSE", "NOTICE"}
        for name in ("LICENSE", "NOTICE"):
            packaged = next(
                item for item in names if item.endswith(".dist-info/licenses/" + name)
            )
            assert archive.read(packaged) == (ROOT / name).read_bytes()
        assert "ems/cli.py" in names and "ems/models.py" in names
    with tarfile.open(ROOT / "dist/employee_management_system-1.0.0.tar.gz") as archive:
        names = archive.getnames()
        check_names(names)
        for suffix in (
            "LICENSE",
            "NOTICE",
            "development-plans/LICENSING.md",
            "scripts/validate_repository.py",
            ".github/dependabot.yml",
            "development-plans/AZURE_ENVIRONMENT.md",
            "development-plans/FREE_SECURITY_HARDENING.md",
            "tests/test_azure.py",
        ):
            assert any(name.endswith("/" + suffix) for name in names)
    print(
        "Wheel and sdist validated: SQL resources, Python metadata, operational docs and no private configuration"
    )


if __name__ == "__main__":
    main()
