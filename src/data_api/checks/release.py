"""Validate release versions and compare public contracts with a PR base commit."""

import argparse
import json
import re
import subprocess
import tomllib
from pathlib import Path
from typing import Any

VERSION_PATTERN = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
CONTRACTS = ("openapi_contract.json", "mcp_contract.json")
CONSTRAINTS = {
    "type",
    "$ref",
    "enum",
    "default",
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "minLength",
    "maxLength",
    "minItems",
    "maxItems",
    "pattern",
    "format",
    "additionalProperties",
    "const",
    "multipleOf",
    "minProperties",
    "maxProperties",
    "uniqueItems",
    "patternProperties",
    "dependentRequired",
    "dependencies",
    "not",
    "allOf",
    "anyOf",
    "oneOf",
    "if",
    "then",
    "else",
    "unevaluatedProperties",
    "contains",
    "minContains",
    "maxContains",
    "propertyNames",
    "prefixItems",
    "items",
    "additionalItems",
}


def version_tuple(value: str) -> tuple[int, ...]:
    if VERSION_PATTERN.fullmatch(value) is None:
        raise ValueError("Expected a stable X.Y.Z version without leading zeroes")
    return tuple(map(int, value.split(".")))


def validate_version(root: Path, tag: str | None = None) -> str:
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    version = project["version"]
    version_tuple(version)
    lock = tomllib.loads((root / "uv.lock").read_text(encoding="utf-8"))
    packages = [package for package in lock["package"] if package["name"] == project["name"]]
    if len(packages) != 1 or packages[0]["version"] != version:
        raise ValueError("pyproject.toml and uv.lock project versions must match")
    if tag is not None and tag != f"v{version}":
        raise ValueError("Release tag must be vX.Y.Z and match the project version")
    return version


def breaking_changes(old: Any, new: Any, path: str = "contract") -> list[str]:
    """Conservative structural guard, not a proof of behavioral compatibility."""
    if isinstance(old, dict) and isinstance(new, dict):
        changes = [
            f"{path}.{key}: removed"
            for key in sorted(old.keys() - new.keys())
            if key != "deprecated"
        ]
        for key in sorted(new.keys() - old.keys()):
            value = new[key]
            if (
                key in CONSTRAINTS
                or (key == "required" and value)
                or (
                    (path.endswith(".parameters") or key == "requestBody")
                    and isinstance(value, dict)
                    and value.get("required")
                )
            ):
                changes.append(f"{path}.{key}: new constraint or required input")
        for key in sorted(old.keys() & new.keys()):
            if key == "deprecated":
                continue
            if key == "enum" and set(old[key]) <= set(new[key]):
                continue
            changes.extend(breaking_changes(old[key], new[key], f"{path}.{key}"))
        return changes
    if old != new:
        return [f"{path}: changed"]
    return []


def git_file(base_sha: str, path: str) -> str:
    if re.fullmatch(r"[a-fA-F0-9]{40,64}", base_sha) is None:
        raise ValueError("Base must be a full commit SHA")
    return subprocess.run(
        ["git", "show", f"{base_sha}:{path}"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout


def compare_base(root: Path, base_sha: str, version: str) -> list[str]:
    previous = tomllib.loads(git_file(base_sha, "pyproject.toml"))["project"]["version"]
    current_version, previous_version = version_tuple(version), version_tuple(previous)
    if current_version < previous_version:
        raise ValueError("Project version must not decrease")
    changes = []
    for name in CONTRACTS:
        path = f"tests/fixtures/{name}"
        # The MCP snapshot is introduced with 3.0.0; older releases have no baseline.
        if name == "mcp_contract.json" and previous_version < (3, 0, 0):
            continue
        old = json.loads(git_file(base_sha, path))
        new = json.loads((root / "tests" / "fixtures" / name).read_text(encoding="utf-8"))
        changes.extend(breaking_changes(old, new, name))
    for change in changes:
        print(change)
    if changes and current_version[0] <= previous_version[0]:
        raise ValueError("Public contract changes require a major version increase")
    return changes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", help="Required vX.Y.Z tag for deployment validation")
    parser.add_argument("--base-sha", help="Compare checked-in contracts against a PR base SHA")
    parser.add_argument("--next-version", help="Validate a proposed version before preparing a PR")
    args = parser.parse_args()
    try:
        version = validate_version(Path.cwd(), args.tag)
        if args.next_version and version_tuple(args.next_version) <= version_tuple(version):
            raise ValueError("New release version must be greater than the current version")
        if args.base_sha:
            compare_base(Path.cwd(), args.base_sha, version)
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"Release validation failed: {exc}\n")
    print(f"Release version validated: {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
