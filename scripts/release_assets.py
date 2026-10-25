"""Check release versions locally; verify and stage built packages in Actions."""

import argparse
import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import tarfile
from collections.abc import Iterable
from email.parser import Parser
from pathlib import Path
from typing import TypeVar
from zipfile import ZipFile

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]
T = TypeVar("T")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def exactly_one(values: Iterable[T], label: str) -> T:
    items = list(values)
    require(len(items) == 1, f"Expected one {label}, found {len(items)}")
    return items[0]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def module_version(source: str) -> str:
    values = [
        ast.literal_eval(node.value)
        for node in ast.parse(source).body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "__version__"
                for target in node.targets)
    ]
    return exactly_one(values, "Python __version__")


def check_versions(tag: str) -> str:
    match = re.fullmatch(r"v([0-9]+\.[0-9]+\.[0-9]+)", tag)
    require(match is not None, f"Expected a release tag such as v2.1.0, got {tag!r}")
    version = match.group(1)
    versions = {
        "Python module": module_version((ROOT / "src/facetmark/__init__.py").read_text(encoding="utf-8")),
        "pyproject.toml": tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"],
        "Cargo.toml": tomllib.loads((ROOT / "desktop/src-tauri/Cargo.toml").read_text(encoding="utf-8"))["package"]["version"],
        "tauri.conf.json": read_json(ROOT / "desktop/src-tauri/tauri.conf.json")["version"],
    }
    cargo = tomllib.loads((ROOT / "desktop/src-tauri/Cargo.lock").read_text(encoding="utf-8"))
    versions["Cargo.lock"] = exactly_one(
        (package["version"] for package in cargo["package"] if package["name"] == "facetmark-desktop"),
        "desktop Cargo package",
    )
    for name in ("desktop", "frontend", "extension"):
        versions[f"{name}/package.json"] = read_json(ROOT / name / "package.json")["version"]
        lock = read_json(ROOT / name / "package-lock.json")
        versions[f"{name}/package-lock.json"] = lock["version"]
        versions[f"{name}/package-lock.json root"] = lock["packages"][""]["version"]
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    versions["CITATION.cff"] = exactly_one(re.findall(r"^version:\s*([^\s]+)\s*$", citation, re.M), "citation version")
    changelog = re.search(r"^## \[([0-9]+\.[0-9]+\.[0-9]+)\] - (\d{4}-\d{2}-\d{2})$",
                          (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"), re.M)
    require(changelog is not None, "Missing versioned changelog entry")
    versions["CHANGELOG.md"] = changelog.group(1)
    for page in ("index", "guide", "measured", "quickstart", "webui", "config", "integrations"):
        for language in ("", ".zh"):
            name = f"{page}{language}.html"
            content = (ROOT / "docs/landing" / name).read_text(encoding="utf-8")
            versions[f"landing/{name}"] = exactly_one(
                set(re.findall(r"facetmark v?([0-9]+\.[0-9]+\.[0-9]+)", content)),
                f"consistent version in {name}",
            )
    date = exactly_one(re.findall(r"^date-released:\s*['\"]?(\d{4}-\d{2}-\d{2})['\"]?\s*$", citation, re.M), "citation release date")
    require(date == changelog.group(2), "Citation and changelog release dates differ")
    for name, actual in versions.items():
        require(actual == version, f"{name}: expected {version}, got {actual}")
    print(f"{tag}: all {len(versions)} source versions agree; release date {date}")
    return version


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stage(args: argparse.Namespace) -> None:
    require(os.environ.get("GITHUB_ACTIONS") == "true", "Stage release packages in GitHub Actions only")
    version = check_versions(args.tag)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    require(commit == os.environ.get("GITHUB_SHA"), "Checkout does not match the Actions commit")
    installer = exactly_one(args.desktop.rglob("*-setup.exe"), "Windows installer")
    with installer.open("rb") as stream:
        require(stream.read(2) == b"MZ", "Installer is not a Windows executable")
    installed = read_json(args.evidence / "installed-desktop.json")
    for name in ("backend_ready", "runtime_absent_before", "network_blocked_for_installers"):
        require(installed.get(name) is True, f"Installation check missing: {name}")
    require(installed["installer_bytes"] == installer.stat().st_size, "Installer size differs from installation evidence")
    require(isinstance(installed.get("signed"), bool), "Missing installer signature result")
    frozen = read_json(args.evidence / "frozen-service.json")
    self_test = exactly_one(
        (check["self_test"] for check in frozen["checks"] if isinstance(check, dict) and "self_test" in check),
        "frozen backend self-test",
    )
    require(self_test.get("version") == version, "Frozen backend version does not match release")
    require(self_test.get("ok") is True and self_test.get("frozen") is True, "Frozen backend self-test failed")
    require(frozen.get("no_python_on_child_path") is True, "Frozen backend was not tested without Python")
    for name in ("real_http_socket", "synthetic_write_read", "independent_token", "rotation_revokes_old_token", "disable_revokes_access"):
        require(frozen.get("mcp", {}).get(name) is True, f"MCP check missing: {name}")
    tray = read_json(args.evidence / "installed-tray.json")
    icon = read_json(args.evidence / "installed-app-icon.json")
    require(tray.get("commit") == commit and icon.get("commit") == commit, "Installed UI evidence is from another commit")
    require(tray.get("whole_frame_visible") is True, "Tray frame was not fully visible")
    lifecycle = read_json(args.evidence / "lifecycle.json")
    for name in ("same_version_reinstall", "uninstall_kept_data", "backend_stopped_with_parent"):
        require(lifecycle.get(name) is True, f"Lifecycle check missing: {name}")

    wheel = exactly_one(args.python.glob("*.whl"), "Python wheel")
    with ZipFile(wheel) as bundle:
        metadata = exactly_one((name for name in bundle.namelist() if name.endswith(".dist-info/METADATA")), "wheel metadata")
        require(Parser().parsestr(bundle.read(metadata).decode())["Version"] == version, "Wheel metadata version differs")
        require(module_version(bundle.read("facetmark/__init__.py").decode()) == version, "Wheel module version differs")
        require("facetmark/web/dist/index.html" in bundle.namelist(), "Shared UI is missing from wheel")
    sdist = exactly_one(args.python.glob("*.tar.gz"), "Python source distribution")
    with tarfile.open(sdist) as bundle:
        project = exactly_one((member for member in bundle.getmembers() if member.name.count("/") == 1 and member.name.endswith("/pyproject.toml")), "source distribution project metadata")
        with bundle.extractfile(project) as stream:
            require(tomllib.loads(stream.read().decode())["project"]["version"] == version, "Source distribution version differs")
    extension = exactly_one(args.extension.glob("*.zip"), "extension ZIP")
    with ZipFile(extension) as bundle:
        manifest = json.loads(bundle.read("manifest.json"))
        require(manifest.get("version") == version and manifest.get("manifest_version") == 3, "Extension manifest version differs")
        require(manifest["background"]["service_worker"] in bundle.namelist(), "Extension service worker is missing")

    args.output.mkdir(parents=True, exist_ok=True)
    require(not any(args.output.iterdir()), "Release output directory must be empty")
    assets = []
    for source, name in (
        (installer, f"facetmark-{version}-windows-x64-setup.exe"),
        (extension, f"facetmark-extension-{version}.zip"),
        (wheel, f"facetmark-{version}-py3-none-any.whl"),
        (sdist, f"facetmark-{version}.tar.gz"),
    ):
        destination = args.output / name
        shutil.copy2(source, destination)
        assets.append({"name": name, "bytes": destination.stat().st_size, "sha256": sha256(destination)})
    manifest_path = args.output / "release-manifest.json"
    manifest_path.write_text(json.dumps({
        "version": version, "tag": args.tag, "commit": commit,
        "build": {
            "workflow": os.environ.get("GITHUB_WORKFLOW"),
            "run_id": os.environ["GITHUB_RUN_ID"],
            "run_attempt": os.environ["GITHUB_RUN_ATTEMPT"],
            "url": f"https://github.com/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{os.environ['GITHUB_RUN_ID']}",
        },
        "verified": {
            "source_and_package_versions": True, "frozen_backend_without_python": True,
            "mcp_real_http_socket_and_token_lifecycle": True, "offline_windows_install": True,
            "installed_tray_and_icon_commit": True, "tray_whole_frame_visible": True,
            "same_version_reinstall": True, "uninstall_kept_data": True,
            "backend_stopped_with_parent": True,
        },
        "windows_installer_signed": installed["signed"], "assets": assets,
    }, indent=2) + "\n", encoding="utf-8")
    checksums = [f"{asset['sha256']}  {asset['name']}" for asset in assets]
    checksums.append(f"{sha256(manifest_path)}  {manifest_path.name}")
    (args.output / "SHA256SUMS.txt").write_text("\n".join(checksums) + "\n", encoding="utf-8")
    print(f"Verified and staged {len(assets)} packages from {commit}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="Read and compare source version metadata")
    check.add_argument("--tag", required=True)
    staging = commands.add_parser("stage", help="Verify and stage packages in Actions")
    staging.add_argument("--tag", required=True)
    for name in ("desktop", "evidence", "python", "extension", "output"):
        staging.add_argument(f"--{name}", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "check":
        check_versions(args.tag)
    else:
        stage(args)


if __name__ == "__main__":
    main()
