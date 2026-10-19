"""Validate release versions and compare public contracts with a PR base commit."""

import argparse
import json
import re
import subprocess
import tomllib
from pathlib import Path
from typing import Any

VERSION_PATTERN = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", re.ASCII)
OPENAPI_CONTRACT = "openapi_contract.json"
MCP_CONTRACT = "mcp_contract.json"
CONTRACTS = (OPENAPI_CONTRACT, MCP_CONTRACT)
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
NAMED_MAPS = {
    "properties": "schema",
    "$defs": "schema",
    "definitions": "schema",
    "patternProperties": "schema",
    "dependentSchemas": "schema",
    "schemas": "schema",
    "operations": "operation",
    "parameters": "parameter",
    "responses": "response",
    "content": "media",
    "headers": "header",
}
SCHEMA_CHILDREN = {
    "input",
    "output",
    "schema",
    "items",
    "additionalProperties",
    "additionalItems",
    "unevaluatedProperties",
    "not",
    "if",
    "then",
    "else",
    "contains",
    "propertyNames",
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


def _resolve_context(path: str, context: str | None) -> str:
    if context is not None:
        return context
    if path.endswith(".parameters"):
        return "map:parameter"
    if path == MCP_CONTRACT:
        return "map:tool"
    if path == OPENAPI_CONTRACT:
        return "document"
    return "schema"


def _is_new_constraint_or_required_input(
    context: str, named_map: bool, key: str, value: Any
) -> bool:
    if context == "schema" and key in CONSTRAINTS:
        return True
    if not named_map and key == "required" and value:
        return True
    is_param_or_request_body = context == "map:parameter" or (
        context == "operation" and key == "requestBody"
    )
    return is_param_or_request_body and isinstance(value, dict) and bool(value.get("required"))


def _child_context(context: str, named_map: bool, key: str) -> str:
    if named_map:
        return context.removeprefix("map:")
    if key in NAMED_MAPS:
        return f"map:{NAMED_MAPS[key]}"
    if context == "schema" and key == "anyOf":
        return "anyOf"
    if context == "schema" and key in {"default", "const", "enum"}:
        return "value"
    if key in SCHEMA_CHILDREN:
        return "schema"
    return "structure"


def _should_skip_shared_key(context: str, key: str, old_val: Any, new_val: Any) -> bool:
    if key == "deprecated" and context in {"schema", "operation"}:
        return True
    return context == "schema" and key == "enum" and all(item in new_val for item in old_val)


def _dict_breaking_changes(
    old: dict[str, Any], new: dict[str, Any], path: str, context: str
) -> list[str]:
    named_map = context.startswith("map:")
    changes = [
        f"{path}.{key}: removed"
        for key in sorted(old.keys() - new.keys())
        if named_map or key != "deprecated" or context not in {"schema", "operation"}
    ]
    for key in sorted(new.keys() - old.keys()):
        if _is_new_constraint_or_required_input(context, named_map, key, new[key]):
            changes.append(f"{path}.{key}: new constraint or required input")
    for key in sorted(old.keys() & new.keys()):
        if _should_skip_shared_key(context, key, old[key], new[key]):
            continue
        child_ctx = _child_context(context, named_map, key)
        changes.extend(breaking_changes(old[key], new[key], f"{path}.{key}", _context=child_ctx))
    return changes


def breaking_changes(
    old: Any, new: Any, path: str = "contract", *, _context: str | None = None
) -> list[str]:
    """Conservative structural guard, not a proof of behavioral compatibility."""
    context = _resolve_context(path, _context)
    if context == "value":
        return [] if old == new else [f"{path}: changed"]
    if isinstance(old, dict) and isinstance(new, dict):
        return _dict_breaking_changes(old, new, path, context)
    if (
        context == "anyOf"
        and isinstance(old, list)
        and isinstance(new, list)
        and len(old) == len(new)
    ):
        return [
            change
            for index, (previous, current) in enumerate(zip(old, new))
            for change in breaking_changes(previous, current, f"{path}[{index}]", _context="schema")
        ]
    return [f"{path}: changed"] if old != new else []


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


def initial_version_is_unpublished(version: str) -> bool:
    """Query the authoritative repository, never infer publication from a shallow clone."""
    if version != "3.0.0":
        return False
    ref = f"refs/tags/v{version}"
    try:
        result = subprocess.run(
            [
                "git",
                "ls-remote",
                "--exit-code",
                "--refs",
                "https://github.com/NTHU-SA/NTHU-Data-API.git",
                ref,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError("Unable to verify release publication") from exc
    if result.returncode == 2 and not result.stdout.strip():
        return True
    if result.returncode == 0 and re.fullmatch(
        rf"[0-9a-f]{{40}}\s+{re.escape(ref)}\s*", result.stdout
    ):
        return False
    raise ValueError("Unable to verify release publication")


def compare_base(
    root: Path, base_sha: str, version: str, *, check_publication: bool = False
) -> list[str]:
    previous = tomllib.loads(git_file(base_sha, "pyproject.toml"))["project"]["version"]
    current_version, previous_version = version_tuple(version), version_tuple(previous)
    if current_version < previous_version:
        raise ValueError("Project version must not decrease")
    changes = []
    for name in CONTRACTS:
        path = f"tests/fixtures/{name}"
        # The MCP snapshot is introduced with 3.0.0; older releases have no baseline.
        if name == MCP_CONTRACT and previous_version < (3, 0, 0):
            continue
        old = json.loads(git_file(base_sha, path))
        new = json.loads((root / "tests" / "fixtures" / name).read_text(encoding="utf-8"))
        changes.extend(breaking_changes(old, new, name))
    for change in changes:
        print(change)
    if (
        changes
        and current_version[0] <= previous_version[0]
        and not (
            check_publication
            and version == previous == "3.0.0"
            and initial_version_is_unpublished(version)
        )
    ):
        raise ValueError("Public contract changes require a major version increase")
    return changes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", help="Required vX.Y.Z tag for deployment validation")
    parser.add_argument("--base-sha", help="Compare checked-in contracts against a PR base SHA")
    parser.add_argument(
        "--check-publication",
        action="store_true",
        help="Verify whether the initial 3.0.0 contract is still unpublished",
    )
    parser.add_argument("--next-version", help="Validate a proposed version before preparing a PR")
    args = parser.parse_args()
    try:
        version = validate_version(Path.cwd(), args.tag)
        if args.next_version and version_tuple(args.next_version) <= version_tuple(version):
            raise ValueError("New release version must be greater than the current version")
        if args.base_sha:
            compare_base(
                Path.cwd(), args.base_sha, version, check_publication=args.check_publication
            )
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"Release validation failed: {exc}\n")
    print(f"Release version validated: {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
