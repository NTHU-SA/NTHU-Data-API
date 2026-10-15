"""Pin public MCP names and input schemas, excluding descriptive metadata."""

import argparse
import asyncio
import json
from pathlib import Path

from fastmcp import Client

from data_api.checks.openapi import contract_differences
from data_api.mcp.server import mcp

BASELINE = Path("tests") / "fixtures" / "mcp_contract.json"


def structural(value):
    if isinstance(value, dict):
        return {
            key: (
                {name: structural(field) for name, field in sorted(item.items())}
                if key in {"properties", "$defs"}
                else structural(item)
            )
            for key, item in sorted(value.items())
            if key not in {"title", "description", "examples", "example"}
        }
    if isinstance(value, list):
        return [structural(item) for item in value]
    return value


async def tool_contract() -> dict:
    async with Client(mcp) as client:
        tools = await client.list_tools()
    return {
        tool.name: {
            "input": structural(tool.input_schema),
            "output": structural(tool.output_schema),
        }
        for tool in sorted(tools, key=lambda tool: tool.name)
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    actual = asyncio.run(tool_contract())
    if args.write:
        BASELINE.write_text(
            json.dumps(actual, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote {BASELINE}")
        return 0
    changes = contract_differences(json.loads(BASELINE.read_text(encoding="utf-8")), actual)
    for change in changes:
        print(change)
    return int(bool(changes))


if __name__ == "__main__":
    raise SystemExit(main())
