"""Download one pinned tool and verify its release SHA-256 before extraction."""

import argparse
import hashlib
import io
import json
import os
import platform
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def install(name):
    if platform.machine().lower() not in ("amd64", "x86_64"):
        raise SystemExit("Pinned CI tools require an x64 machine")
    tool = json.loads((ROOT / ".github/ci-tools.json").read_text())[name]
    release = tool[sys.platform]
    url = f"https://github.com/{tool['repository']}/releases/download/v{tool['version']}/{release['asset']}"
    with urllib.request.urlopen(url, timeout=60) as response:
        archive = response.read()
    if hashlib.sha256(archive).hexdigest() != release["sha256"]:
        raise SystemExit("Release checksum mismatch; refusing to install")
    binary = name + (".exe" if sys.platform == "win32" else "")
    if release["asset"].endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(archive)) as source:
            content = source.read(binary)
    else:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as source:
            member = source.getmember(binary)
            if not member.isfile():
                raise SystemExit("Release binary is not a regular file")
            content = source.extractfile(member).read()
    destination = ROOT / ".local/ci-tools" / binary
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".download")
    temporary.write_bytes(content)
    temporary.chmod(0o755)
    os.replace(temporary, destination)
    print(f"Installed {name} {tool['version']}; release SHA-256 verified")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tool", choices=("actionlint", "gitleaks"))
    install(parser.parse_args().tool)
