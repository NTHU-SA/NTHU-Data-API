"""Structured compatibility baseline, excluding documentation-only metadata."""

import argparse
import json
from pathlib import Path
from typing import Any

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}
DOCUMENTATION_KEYS = {"title", "description", "summary", "examples", "example", "externalDocs"}


def contract_projection(schema: dict[str, Any]) -> dict[str, Any]:
    def strip_docs(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: (
                    {name: strip_docs(field) for name, field in sorted(item.items())}
                    if key in {"properties", "$defs"}
                    else strip_docs(item)
                )
                for key, item in sorted(value.items())
                if key not in DOCUMENTATION_KEYS
            }
        if isinstance(value, list):
            return [strip_docs(item) for item in value]
        return value

    operations = {}
    for path, path_item in sorted(schema["paths"].items()):
        for method, operation in sorted(path_item.items()):
            if method not in HTTP_METHODS:
                continue
            parameters = {
                f"{parameter['in']}:{parameter['name']}": {
                    "required": parameter.get("required", False),
                    "schema": strip_docs(parameter["schema"]),
                }
                for parameter in operation.get("parameters", [])
            }
            operations[f"{method.upper()} {path}"] = {
                "operationId": operation["operationId"],
                "deprecated": operation.get("deprecated", False),
                "parameters": parameters,
                "requestBody": strip_docs(operation.get("requestBody")),
                "responses": strip_docs(operation["responses"]),
            }
    return {
        "operations": operations,
        "schemas": strip_docs(schema.get("components", {}).get("schemas", {})),
    }


def contract_differences(expected: Any, actual: Any, path: str = "contract") -> list[str]:
    if isinstance(expected, dict) and isinstance(actual, dict):
        changes = [f"{path}.{key}: removed" for key in sorted(expected.keys() - actual.keys())]
        changes += [f"{path}.{key}: added" for key in sorted(actual.keys() - expected.keys())]
        for key in sorted(expected.keys() & actual.keys()):
            changes.extend(contract_differences(expected[key], actual[key], f"{path}.{key}"))
        return changes
    if expected != actual:
        return [f"{path}: changed from {expected!r} to {actual!r}"]
    return []


def main() -> int:
    from data_api.api.api import app

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--baseline", type=Path, default=Path("tests") / "fixtures" / "openapi_contract.json"
    )
    parser.add_argument(
        "--write", action="store_true", help="Regenerate only for reviewed API changes"
    )
    args = parser.parse_args()
    actual = contract_projection(app.openapi())
    if args.write:
        args.baseline.write_text(
            json.dumps(actual, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote {args.baseline}")
        return 0
    expected = json.loads(args.baseline.read_text(encoding="utf-8"))
    changes = contract_differences(expected, actual)
    for change in changes:
        print(change)
    return int(bool(changes))


if __name__ == "__main__":
    raise SystemExit(main())
