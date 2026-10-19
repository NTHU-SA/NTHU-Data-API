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


@pytest.mark.parametrize("value", ["3", "3.0", "v3.0.0", "03.0.0", "3.0.0rc1", "3.0.0\n", "3.０.0"])
def test_nonstable_versions_rejected(value):
    with pytest.raises(ValueError, match="stable"):
        release.version_tuple(value)


@pytest.mark.parametrize("tag", ["", "3.0.0", "v2.0.0", "v3.0.0-rc.1", "v03.0.0"])
def test_invalid_or_mismatched_tags_fail(tag):
    root = Path.cwd()
    with pytest.raises(ValueError, match="tag"):
        release.validate_version(root, tag)


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
    "code,stdout,expected",
    [
        (2, "", True),
        (0, "a" * 40 + "\trefs/tags/v3.0.0\n", False),
        (128, "", None),
        (0, "", None),
        (2, "unexpected", None),
        (0, "a" * 40 + "\trefs/tags/v3.0.1\n", None),
    ],
)
def test_publication_uses_authoritative_remote_and_fails_closed(
    monkeypatch, code, stdout, expected
):
    from types import SimpleNamespace

    def run(args, **kwargs):
        assert args == [
            "git",
            "ls-remote",
            "--exit-code",
            "--refs",
            "https://github.com/NTHU-SA/NTHU-Data-API.git",
            "refs/tags/v3.0.0",
        ]
        assert kwargs["timeout"] == 30
        return SimpleNamespace(returncode=code, stdout=stdout)

    monkeypatch.setattr(release.subprocess, "run", run)
    if expected is None:
        with pytest.raises(ValueError, match="Unable to verify"):
            release.initial_version_is_unpublished("3.0.0")
    else:
        assert release.initial_version_is_unpublished("3.0.0") is expected
    assert release.initial_version_is_unpublished("3.0.1") is False


@pytest.mark.parametrize("failure", [OSError(), release.subprocess.TimeoutExpired("git", 30)])
def test_publication_network_failure_is_not_unpublished(monkeypatch, failure):
    def run(*args, **kwargs):
        raise failure

    monkeypatch.setattr(release.subprocess, "run", run)
    with pytest.raises(ValueError, match="Unable to verify"):
        release.initial_version_is_unpublished("3.0.0")


@pytest.mark.parametrize("unpublished", [True, False, None])
@pytest.mark.parametrize("current", ["3.0.0", "3.0.1", "2.9.0", "4.0.0"])
def test_only_verified_unpublished_initial_version_can_update_contract(
    monkeypatch, tmp_path, unpublished, current
):
    fixtures = tmp_path / "tests" / "fixtures"
    fixtures.mkdir(parents=True)
    for name in release.CONTRACTS:
        (fixtures / name).write_text("{}", encoding="utf-8")

    def git_file(sha, path):
        return '[project]\nversion="3.0.0"\n' if path == "pyproject.toml" else '{"old": {}}'

    def publication(version):
        if unpublished is None:
            raise ValueError("Unable to verify release publication")
        return unpublished

    monkeypatch.setattr(release, "git_file", git_file)
    monkeypatch.setattr(release, "initial_version_is_unpublished", publication)
    if current == "4.0.0" or (current == "3.0.0" and unpublished is True):
        assert release.compare_base(tmp_path, "a" * 40, current, check_publication=True)
    else:
        with pytest.raises(ValueError):
            release.compare_base(tmp_path, "a" * 40, current, check_publication=True)
    if current == "3.0.0":
        with pytest.raises(ValueError, match="major"):
            release.compare_base(tmp_path, "a" * 40, current)


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


@pytest.mark.parametrize("name", ["deprecated", "type"])
@pytest.mark.parametrize("container", ["properties", "$defs", "definitions", "schemas"])
def test_schema_names_are_not_keywords(name, container):
    old = {container: {name: {"type": "string"}}}
    new = {container: {name: {"type": "integer"}}}
    assert release.breaking_changes(old, new) == [f"contract.{container}.{name}.type: changed"]
    assert release.breaking_changes(old, {container: {}}) == [
        f"contract.{container}.{name}: removed"
    ]


def test_optional_type_named_argument_is_not_a_constraint():
    old = {"get_bus_schedule": {"input": {"properties": {}}}}
    new = {
        "get_bus_schedule": {
            "input": {"properties": {"type": {"type": "string"}, "required": {"type": "string"}}}
        }
    }
    assert not release.breaking_changes(old, new, "mcp_contract.json")
    assert release.breaking_changes(new, old, "mcp_contract.json") == [
        "mcp_contract.json.get_bus_schedule.input.properties.required: removed",
        "mcp_contract.json.get_bus_schedule.input.properties.type: removed",
    ]


def test_tool_and_parameter_names_are_not_schema_keywords():
    assert not release.breaking_changes({}, {"type": {"input": {}}}, "mcp_contract.json")
    assert release.breaking_changes(
        {"operations": {"GET /test": {"parameters": {"deprecated": {"required": False}}}}},
        {"operations": {"GET /test": {"parameters": {}}}},
        "openapi_contract.json",
    ) == ["openapi_contract.json.operations.GET /test.parameters.deprecated: removed"]


@pytest.mark.parametrize("keyword", ["default", "const", "enum"])
def test_literal_schema_values_do_not_reenter_schema_context(keyword):
    old_value = {"input": {"deprecated": "old"}}
    new_value = {"input": {"deprecated": "new"}}
    old = {keyword: [old_value] if keyword == "enum" else old_value}
    new = {keyword: [new_value] if keyword == "enum" else new_value}
    assert release.breaking_changes(old, new) == [f"contract.{keyword}: changed"]
    if keyword == "enum":
        assert not release.breaking_changes(old, {"enum": [old_value, new_value]})


@pytest.mark.parametrize("keyword", ["additionalItems", "unevaluatedProperties"])
def test_schema_valued_keywords_propagate_context(keyword):
    assert release.breaking_changes({keyword: {}}, {keyword: {"type": "string"}}) == [
        f"contract.{keyword}.type: new constraint or required input"
    ]


@pytest.mark.parametrize("change", ["extension", "narrowed", "branch", "removed_branch"])
def test_nullable_stop_enum_compatibility(change):
    old = json.loads(BASELINE.read_text(encoding="utf-8"))
    new = deepcopy(old)
    stop = new["get_bus_schedule"]["input"]["properties"]["stop"]
    if change == "extension":
        stop["anyOf"][0]["enum"].append("additional stop")
    elif change == "narrowed":
        stop["anyOf"][0]["enum"].pop()
    elif change == "branch":
        stop["anyOf"][1]["type"] = "integer"
    else:
        stop["anyOf"].pop()
    changes = release.breaking_changes(old, new, "mcp_contract.json")
    if change == "extension":
        assert not changes
    else:
        assert changes


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


@pytest.mark.parametrize(
    "change,breaking",
    [
        ("remove_deprecated", True),
        ("change_deprecated", True),
        ("add_optional_type", False),
        ("extend_stop_enum", False),
        ("change_nullable_branch", True),
        ("change_default_literal", True),
        ("restrict_additional_items", True),
        ("restrict_unevaluated_properties", True),
    ],
)
def test_same_major_mcp_snapshot_changes(monkeypatch, change, breaking):
    old = json.loads(BASELINE.read_text(encoding="utf-8"))
    new = deepcopy(old)
    old_properties = old["get_bus_schedule"]["input"]["properties"]
    new_properties = new["get_bus_schedule"]["input"]["properties"]
    if change == "remove_deprecated":
        old_properties["deprecated"] = {"type": "string"}
    elif change == "change_deprecated":
        old_properties["deprecated"] = {"type": "string"}
        new_properties["deprecated"] = {"type": "integer"}
    elif change == "add_optional_type":
        new_properties["type"] = {"type": "string"}
    elif change == "extend_stop_enum":
        old_properties["stop"]["anyOf"][0]["enum"].pop()
    elif change == "change_nullable_branch":
        new_properties["stop"]["anyOf"][1]["type"] = "integer"
    elif change == "change_default_literal":
        old_properties["stop"]["default"] = {"input": {"deprecated": "old"}}
        new_properties["stop"]["default"] = {"input": {"deprecated": "new"}}
    else:
        keyword = (
            "additionalItems" if change == "restrict_additional_items" else "unevaluatedProperties"
        )
        old_properties["stop"][keyword] = {}
        new_properties["stop"][keyword] = {"type": "string"}

    original_read_text = Path.read_text

    def read_text(path, *args, **kwargs):
        if path == Path.cwd() / BASELINE:
            return json.dumps(new)
        return original_read_text(path, *args, **kwargs)

    def git_file(sha, path):
        if path == "pyproject.toml":
            return '[project]\nversion="3.0.0"\n'
        if path.endswith("mcp_contract.json"):
            return json.dumps(old)
        return original_read_text(Path(path), encoding="utf-8")

    monkeypatch.setattr(Path, "read_text", read_text)
    monkeypatch.setattr(release, "git_file", git_file)
    root = Path.cwd()
    if breaking:
        with pytest.raises(ValueError, match="major"):
            release.compare_base(root, "a" * 40, "3.0.1")
    else:
        assert not release.compare_base(root, "a" * 40, "3.0.1")


async def test_mcp_structured_baseline():
    assert await tool_contract() == json.loads(BASELINE.read_text(encoding="utf-8"))


def test_mcp_field_named_title_is_not_stripped():
    schema = {"title": "Description", "properties": {"title": {"type": "string"}}}
    original = deepcopy(schema)
    assert structural(schema) == {"properties": {"title": {"type": "string"}}}
    assert schema == original
