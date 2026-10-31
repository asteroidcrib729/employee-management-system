"""Scan publishable working files, including new files, without reading ignored secrets."""

import secrets
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    files = (
        subprocess.check_output(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            cwd=ROOT,
        )
        .decode()
        .split("\0")
    )
    tool = (
        ROOT
        / ".local/ci-tools"
        / ("gitleaks.exe" if sys.platform == "win32" else "gitleaks")
    )
    # Check the detector and redaction using a generated, nonfunctional secret.
    synthetic = "Detector9!" + secrets.token_hex(20)
    detection = subprocess.run(
        [
            str(tool),
            "stdin",
            "--redact",
            "--no-banner",
            "--config",
            str(ROOT / ".gitleaks.toml"),
        ],
        input=f"EMS_CONNECTION_STRING=PWD={{{synthetic}}};\n",
        capture_output=True,
        text=True,
        check=False,
    )
    if detection.returncode != 1 or synthetic in detection.stdout + detection.stderr:
        raise SystemExit("Secret detector/redaction self-test failed")
    print(
        "Secret detector self-test passed; generated fixture was detected and redacted",
        flush=True,
    )
    with tempfile.TemporaryDirectory(prefix="ems-source-scan-") as directory:
        snapshot = Path(directory)
        for name in set(files) - {""}:
            source = ROOT / name
            if source.is_symlink():
                raise SystemExit(
                    "Refusing to follow a source symlink during secret scanning"
                )
            if not source.is_file():
                continue
            if not source.resolve().is_relative_to(ROOT):
                raise SystemExit("Source path escapes repository")
            destination = snapshot / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        return subprocess.run(
            [
                str(tool),
                "dir",
                "--redact",
                "--no-banner",
                "--config",
                str(ROOT / ".gitleaks.toml"),
                "--max-archive-depth",
                "2",
                str(snapshot),
            ],
            check=False,
        ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
