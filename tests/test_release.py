"""Release metadata and conservative public compatibility gates."""

import json
from copy import deepcopy
from importlib.metadata import version
from pathlib import Path

import pytest

from data_api import __version__
from data_api.api.api import app
from data_api.checks import release
from data_api.checks.mcp import BASELINE, structural, tool_contract
from data_api.mcp.server import mcp


def test_installed_version_has_one_source():
    assert release.validate_version(Path.cwd(), f"v{__version__}") == __version__
    assert __version__ == app.version == version("nthu-data-api")
    assert mcp.version == __version__


@pytest.mark.parametrize("value", ["3", "3.0", "v3.0.0", "03.0.0", "3.0.0rc1", "3.0.0\n"])
def test_nonstable_versions_rejected(value):
    with pytest.raises(ValueError, match="stable"):
        release.version_tuple(value)


@pytest.mark.parametrize("tag", ["", "3.0.0", "v2.0.0", "v3.0.0-rc.1", "v03.0.0"])
def test_invalid_or_mismatched_tags_fail(tag):
    with pytest.raises(ValueError, match="tag"):
        release.validate_version(Path.cwd(), tag)


def test_lock_mismatch_fails(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname="nthu-data-api"\nversion="3.0.0"\n', encoding="utf-8"
    )
    (tmp_path / "uv.lock").write_text(
        '[[package]]\nname="nthu-data-api"\nversion="2.0.0"\n', encoding="utf-8"
    )
    with pytest.raises(ValueError, match="must match"):
        release.validate_version(tmp_path)


@pytest.mark.parametrize(
    "old,new",
    [
        ({"GET /courses": {}}, {}),
        ({"type": "string"}, {"type": "integer"}),
        ({"enum": ["a", "b"]}, {"enum": ["a"]}),
        ({}, {"minimum": 1}),
        ({}, {"type": "integer"}),
        ({}, {"enum": ["only"]}),
        ({}, {"default": 20}),
        ({"required": []}, {"required": ["name"]}),
        ({"default": 5}, {"default": 20}),
    ],
)
def test_breaking_changes_detected(old, new):
    assert release.breaking_changes(old, new)


def test_new_required_parameter_is_breaking():
    assert release.breaking_changes({}, {"query:limit": {"required": True}}, "contract.parameters")


@pytest.mark.parametrize(
    "old,new",
    [
        ({}, {"GET /new": {"responses": {}}}),
        ({}, {"query:new": {"required": False, "schema": {"type": "string"}}}),
        ({"enum": ["a"]}, {"enum": ["a", "b"]}),
        ({"deprecated": False}, {"deprecated": True}),
        ({"properties": {}}, {"properties": {"title": {"type": "string"}}}),
        ({}, {"NewSchema": {"type": "object", "required": ["id"]}}),
    ],
)
def test_compatible_additions_allowed(old, new):
    assert not release.breaking_changes(old, new)


@pytest.mark.parametrize("current,allowed", [("3.0.1", False), ("4.0.0", True)])
def test_refreshed_baseline_cannot_hide_same_major_removal(monkeypatch, tmp_path, current, allowed):
    fixtures = tmp_path / "tests" / "fixtures"
    fixtures.mkdir(parents=True)
    for name in release.CONTRACTS:
        (fixtures / name).write_text("{}", encoding="utf-8")

    def git_file(sha, path):
        if path == "pyproject.toml":
            return '[project]\nversion="3.0.0"\n'
        return '{"public-operation": {}}'

    monkeypatch.setattr(release, "git_file", git_file)
    if allowed:
        assert release.compare_base(tmp_path, "a" * 40, current)
    else:
        with pytest.raises(ValueError, match="major"):
            release.compare_base(tmp_path, "a" * 40, current)


async def test_mcp_structured_baseline():
    assert await tool_contract() == json.loads(BASELINE.read_text(encoding="utf-8"))


def test_mcp_field_named_title_is_not_stripped():
    schema = {"title": "Description", "properties": {"title": {"type": "string"}}}
    original = deepcopy(schema)
    assert structural(schema) == {"properties": {"title": {"type": "string"}}}
    assert schema == original
