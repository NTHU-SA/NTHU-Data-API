"""Cloud Run promotion and rollback without contacting GCP."""

import json
import subprocess
from argparse import Namespace
from copy import deepcopy
from pathlib import Path

import httpx
import pytest

from data_api.checks import cloud_run_release as deploy
from data_api.checks.smoke import check_version


@pytest.fixture
def cloud(monkeypatch, tmp_path):
    monkeypatch.setattr(deploy, "STATE", tmp_path / "state.json")
    monkeypatch.setattr(deploy, "TOKEN", tmp_path / "token")
    image = tmp_path / "image.txt"
    image.write_text(
        "asia-east1-docker.pkg.dev/project/repository/api@sha256:" + "a" * 64,
        encoding="utf-8",
    )
    args = Namespace(
        project="project",
        region="asia-east1",
        service="data-api",
        lock_bucket="release-locks",
        smoke_account="smoke@project.iam.gserviceaccount.com",
        build_id="abcdefgh-1234",
        image_file=str(image),
    )
    previous = {
        "status": {
            "url": "https://data-api.run.app",
            "traffic": [
                {"revisionName": "old-a", "percent": 80},
                {"revisionName": "old-b", "percent": 20},
            ],
        }
    }
    calls = []

    def gcloud(*command):
        calls.append(command)
        if command[:3] == ("run", "services", "describe"):
            return json.dumps(previous)
        if command[:2] == ("run", "deploy"):
            result = deepcopy(previous)
            result["status"]["traffic"].append(
                {
                    "tag": "release-abcdefgh-123",
                    "revisionName": "candidate",
                    "url": "https://candidate.run.app",
                }
            )
            return json.dumps(result)
        if command[:3] == ("storage", "objects", "describe"):
            return "12345"
        if command[:2] == ("auth", "print-identity-token"):
            return "private-token"
        return ""

    monkeypatch.setattr(deploy, "gcloud", gcloud)
    return args, calls, previous


def test_prepare_deploys_digest_without_traffic_and_locks(cloud):
    args, calls, _ = cloud
    deploy.prepare(args)
    state = json.loads(deploy.STATE.read_text(encoding="utf-8"))
    assert state["traffic"] == {"old-a": 80, "old-b": 20}
    assert state["candidate"] == "candidate"
    assert deploy.TOKEN.read_text(encoding="utf-8") == "private-token"
    assert calls[0][:3] == ("storage", "cp", "--if-generation-match=0")
    deployment = next(call for call in calls if call[:2] == ("run", "deploy"))
    assert "--no-traffic" in deployment
    assert any("@sha256:" in argument for argument in deployment)
    assert not any("--to-revisions" in call for call in calls)


def test_success_promotes_then_cleans_up(cloud, tmp_path):
    args, calls, _ = cloud
    deploy.prepare(args)
    state = json.loads(deploy.STATE.read_text(encoding="utf-8"))
    success = tmp_path / "success"
    success.touch()
    deploy.promote(state, success)
    deploy.finalize(state, success)
    assert any("candidate=100" in call for call in calls)
    assert calls[-1] == ("storage", "rm", state["lock"], "--if-generation-match=12345")
    assert not deploy.TOKEN.exists()


def test_candidate_failure_never_promotes(cloud, tmp_path):
    args, calls, _ = cloud
    deploy.prepare(args)
    state = json.loads(deploy.STATE.read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="Candidate smoke failed"):
        deploy.promote(state, tmp_path / "missing")
    assert not any("--to-revisions" in call for call in calls)
    assert calls[-1][0:2] == ("storage", "rm")


def test_production_failure_restores_exact_previous_split(cloud, tmp_path):
    args, calls, _ = cloud
    deploy.prepare(args)
    state = json.loads(deploy.STATE.read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="restored"):
        deploy.finalize(state, tmp_path / "missing")
    assert any("old-a=80,old-b=20" in call for call in calls)
    assert calls[-1][0:2] == ("storage", "rm")


def test_external_traffic_change_blocks_promotion(cloud, tmp_path):
    args, calls, previous = cloud
    deploy.prepare(args)
    state = json.loads(deploy.STATE.read_text(encoding="utf-8"))
    previous["status"]["traffic"] = [{"revisionName": "external", "percent": 100}]
    success = tmp_path / "success"
    success.touch()
    with pytest.raises(ValueError, match="outside"):
        deploy.promote(state, success)
    assert not any("--to-revisions" in call for call in calls)


@pytest.mark.parametrize("phase", ["prepare", "promote"])
def test_gcloud_failure_restores_traffic_and_unlocks(cloud, monkeypatch, tmp_path, phase):
    args, calls, _ = cloud
    if phase == "promote":
        deploy.prepare(args)
    original = deploy.gcloud
    failed = False

    def fail(*command):
        nonlocal failed
        if not failed and (
            command[:2] == ("run", "deploy") or (phase == "promote" and "candidate=100" in command)
        ):
            failed = True
            raise subprocess.CalledProcessError(1, command)
        return original(*command)

    monkeypatch.setattr(deploy, "gcloud", fail)
    with pytest.raises(subprocess.CalledProcessError):
        if phase == "prepare":
            deploy.prepare(args)
        else:
            success = tmp_path / "success"
            success.touch()
            deploy.promote(json.loads(deploy.STATE.read_text(encoding="utf-8")), success)
    assert any("old-a=80,old-b=20" in call for call in calls)
    assert calls[-1][0:2] == ("storage", "rm")


def test_lock_acquisition_failure_does_not_delete_another_build_lock(cloud, monkeypatch):
    args, calls, _ = cloud

    def locked(*command):
        calls.append(command)
        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(deploy, "gcloud", locked)
    with pytest.raises(subprocess.CalledProcessError):
        deploy.prepare(args)
    assert len(calls) == 1


def test_token_removed_even_when_unlock_fails(cloud, monkeypatch, tmp_path):
    args, _, _ = cloud
    deploy.prepare(args)
    state = json.loads(deploy.STATE.read_text(encoding="utf-8"))
    original = deploy.gcloud

    def fail(*command):
        if command[:2] == ("storage", "rm"):
            raise subprocess.CalledProcessError(1, command)
        return original(*command)

    monkeypatch.setattr(deploy, "gcloud", fail)
    success = tmp_path / "success"
    success.touch()
    with pytest.raises(subprocess.CalledProcessError):
        deploy.finalize(state, success)
    assert not deploy.TOKEN.exists()


def test_failed_promotion_preflight_unlocks(cloud, monkeypatch, tmp_path):
    args, calls, _ = cloud
    deploy.prepare(args)
    state = json.loads(deploy.STATE.read_text(encoding="utf-8"))
    original = deploy.gcloud

    def fail(*command):
        if command[:3] == ("run", "services", "describe"):
            raise subprocess.CalledProcessError(1, command)
        return original(*command)

    monkeypatch.setattr(deploy, "gcloud", fail)
    success = tmp_path / "success"
    success.touch()
    with pytest.raises(subprocess.CalledProcessError):
        deploy.promote(state, success)
    assert calls[-1][:2] == ("storage", "rm")


@pytest.mark.parametrize("setting,value", [("project", ""), ("service", "*"), ("build_id", "../")])
def test_invalid_settings_fail_before_cloud_access(cloud, setting, value):
    args, calls, _ = cloud
    setattr(args, setting, value)
    with pytest.raises(ValueError):
        deploy.prepare(args)
    assert not calls


def test_mutable_image_is_rejected(cloud):
    args, calls, _ = cloud
    Path(args.image_file).write_text("registry/api:latest", encoding="utf-8")
    with pytest.raises(ValueError, match="immutable"):
        deploy.prepare(args)
    assert not calls


def test_first_deployment_requires_explicit_bootstrap():
    with pytest.raises(ValueError, match="existing service"):
        deploy.allocation({"status": {"traffic": []}})


@pytest.mark.parametrize("actual,expected", [("3.0.0", False), ("2.0.0", True)])
async def test_smoke_verifies_release_metadata(actual, expected):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={
                    "name": "NTHU Data API",
                    "version": actual,
                    "docs": "/docs",
                    "openapi": "/openapi.json",
                    "mcp": "/mcp",
                },
            )
        )
    ) as client:
        assert bool(await check_version(client, "https://test", "3.0.0")) is expected


async def test_invalid_discovery_fails_smoke():
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={}))
    ) as client:
        failures = await check_version(client, "https://test", "3.0.0")
    assert failures[0].stage == "response-schema"
