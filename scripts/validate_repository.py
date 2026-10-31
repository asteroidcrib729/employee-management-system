"""Validate release configuration, workflow policy, documentation and legacy integrity."""

import hashlib
import json
import re
import subprocess
import tomllib
import zipfile
from pathlib import Path
from urllib.parse import unquote

import yaml

ROOT = Path(__file__).resolve().parents[1]


class UniqueLoader(yaml.BaseLoader):
    def construct_mapping(self, node, deep=False):
        result = {}
        for key, value in node.value:
            key = self.construct_object(key, deep=deep)
            if key in result:
                raise ValueError(f"Duplicate YAML key: {key}")
            result[key] = self.construct_object(value, deep=deep)
        return result


def main():
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text())
    python = (ROOT / ".python-version").read_text().strip()
    assert metadata["project"]["requires-python"] == "==" + python
    assert python == "3.14.7"
    assert not (ROOT / ".env").exists(), "Obsolete localhost .env must not return"
    files = (
        subprocess.check_output(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            cwd=ROOT,
        )
        .decode()
        .split("\0")
    )
    for name in set(files) - {""}:
        path = ROOT / name
        if not path.is_file():
            continue
        assert not name.startswith((".local/", ".venv/", ".uv-cache/")), (
            "Private/generated file is publishable"
        )
        assert not (path.name.startswith(".env") and path.name != ".env.example"), (
            "Private environment file is publishable"
        )
        if path.suffix == ".py":
            compile(path.read_text(encoding="utf-8"), name, "exec")
        if path.suffix == ".md":
            for target in re.findall(
                r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")
            ):
                if "://" not in target and not target.startswith("#"):
                    target = unquote(target.split("#", 1)[0].strip("<>"))
                    assert (path.parent / target).exists(), (
                        f"Broken local link in {name}: {target}"
                    )
    for path in (ROOT / ".github/workflows").glob("*.yml"):
        data = yaml.load(path.read_text(), Loader=UniqueLoader)
        assert {"push", "pull_request"} <= data["on"].keys()
        assert "pull_request_target" not in data["on"]
        assert data["permissions"] == {"contents": "read"}
        for job in data["jobs"].values():
            assert int(job["timeout-minutes"]) <= 30
            for step in job["steps"]:
                if "uses" in step:
                    assert re.fullmatch(r"[\w./-]+@[0-9a-f]{40}", step["uses"]), (
                        "Action must use an immutable commit"
                    )
                assert "EMS_AZURE_TESTS" not in str(step), (
                    "Azure credentials/tests do not belong in public CI"
                )
    dependabot = yaml.load(
        (ROOT / ".github/dependabot.yml").read_text(), Loader=UniqueLoader
    )
    assert dependabot["version"] == "2"
    assert {item["package-ecosystem"] for item in dependabot["updates"]} == {
        "uv",
        "github-actions",
    }
    for tool in json.loads((ROOT / ".github/ci-tools.json").read_text()).values():
        for system in ("linux", "win32"):
            assert re.fullmatch("[0-9a-f]{64}", tool[system]["sha256"])
    legacy = ROOT / "development-plans/legacy"
    hashes = json.loads((legacy / "original-hashes.json").read_text())
    with zipfile.ZipFile(legacy / "original-source.zip") as archive:
        for name, expected in hashes.items():
            content = (
                archive.read(name)
                if name in archive.namelist()
                else (legacy / Path(name).name).read_bytes()
            )
            assert hashlib.sha256(content).hexdigest() == expected, (
                f"Legacy artifact changed: {name}"
            )
    print(
        "Repository validation passed: Python pin, source syntax, YAML, action pins, private-file boundaries, links and ten original hashes"
    )


if __name__ == "__main__":
    main()
