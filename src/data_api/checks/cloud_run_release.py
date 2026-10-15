"""Cloud Build release phases; stdlib-only so the Cloud SDK can execute this file."""

import argparse
import json
import re
import subprocess
from pathlib import Path

STATE = Path("/workspace/release-state.json")
TOKEN = Path("/workspace/release-token")
DEPLOY_ERRORS = (subprocess.CalledProcessError, ValueError, KeyError, OSError)


def gcloud(*args: str) -> str:
    return subprocess.run(
        ["gcloud", "--quiet", *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def describe(state: dict) -> dict:
    return json.loads(
        gcloud(
            "run",
            "services",
            "describe",
            state["service"],
            "--project",
            state["project"],
            "--region",
            state["region"],
            "--format=json",
        )
    )


def allocation(service: dict) -> dict[str, int]:
    traffic = {}
    for target in service["status"].get("traffic", []):
        percent = target.get("percent", 0)
        if percent:
            revision = target["revisionName"]
            traffic[revision] = traffic.get(revision, 0) + percent
    if sum(traffic.values()) != 100:
        raise ValueError("An existing service with a complete traffic allocation is required")
    return traffic


def set_traffic(state: dict, traffic: dict[str, int]) -> None:
    gcloud(
        "run",
        "services",
        "update-traffic",
        state["service"],
        "--project",
        state["project"],
        "--region",
        state["region"],
        "--to-revisions",
        ",".join(f"{name}={percent}" for name, percent in traffic.items()),
    )


def cleanup(state: dict) -> None:
    try:
        if state.get("candidate_tag"):
            gcloud(
                "run",
                "services",
                "update-traffic",
                state["service"],
                "--project",
                state["project"],
                "--region",
                state["region"],
                "--remove-tags",
                state["candidate_tag"],
            )
    finally:
        try:
            gcloud(
                "storage",
                "rm",
                state["lock"],
                f"--if-generation-match={state['generation']}",
            )
        finally:
            TOKEN.unlink(missing_ok=True)


def prepare(args) -> None:
    image = Path(args.image_file).read_text(encoding="utf-8").strip()
    if re.fullmatch(r"[a-z0-9.-]+-docker\.pkg\.dev/[^@\s]+@sha256:[a-f0-9]{64}", image) is None:
        raise ValueError("Deployment requires an immutable Artifact Registry image digest")
    for name in ("project", "region", "service", "lock_bucket", "smoke_account", "build_id"):
        if not getattr(args, name):
            raise ValueError(f"Missing deployment setting: {name}")
    for name in ("project", "region", "service", "lock_bucket"):
        if re.fullmatch(r"[a-z0-9][a-z0-9._-]*[a-z0-9]", getattr(args, name)) is None:
            raise ValueError(f"Invalid deployment setting: {name}")
    if re.fullmatch(r"[a-zA-Z0-9-]+", args.build_id) is None:
        raise ValueError("Invalid Cloud Build ID")
    state = {
        "project": args.project,
        "region": args.region,
        "service": args.service,
        "lock": f"gs://{args.lock_bucket}/{args.region}-{args.service}.release-lock",
        "build_id": args.build_id,
    }
    owner = STATE.with_name("release-owner.json")
    owner.write_text(json.dumps(state), encoding="utf-8")
    # An atomic create prevents two builds from modifying service traffic together.
    gcloud("storage", "cp", "--if-generation-match=0", str(owner), state["lock"])
    state["generation"] = gcloud(
        "storage", "objects", "describe", state["lock"], "--format=value(generation)"
    )
    STATE.write_text(json.dumps(state), encoding="utf-8")
    try:
        before = describe(state)
        state["traffic"] = allocation(before)
        state["service_url"] = before["status"]["url"]
        state["candidate_tag"] = f"release-{args.build_id[:12].lower()}"
        STATE.write_text(json.dumps(state), encoding="utf-8")
        deployed = json.loads(
            gcloud(
                "run",
                "deploy",
                args.service,
                "--project",
                args.project,
                "--region",
                args.region,
                "--image",
                image,
                "--no-traffic",
                "--tag",
                state["candidate_tag"],
                "--format=json",
            )
        )
        target = next(
            (
                target
                for target in deployed["status"]["traffic"]
                if target.get("tag") == state["candidate_tag"]
            ),
            None,
        )
        if target is None:
            raise ValueError("Candidate revision URL is unavailable")
        state["candidate"] = target["revisionName"]
        state["candidate_url"] = target["url"]
        if target.get("percent", 0) != 0 or allocation(deployed) != state["traffic"]:
            raise ValueError("Candidate deployment unexpectedly changed production traffic")
        STATE.write_text(json.dumps(state), encoding="utf-8")
        token = gcloud(
            "auth",
            "print-identity-token",
            "--impersonate-service-account",
            args.smoke_account,
            "--audiences",
            state["service_url"],
        )
        if not token:
            raise ValueError("Unable to obtain smoke identity token")
        TOKEN.write_text(token, encoding="utf-8")
        TOKEN.chmod(0o600)
    except DEPLOY_ERRORS:
        try:
            if state.get("traffic"):
                set_traffic(state, state["traffic"])
        finally:
            cleanup(state)
        raise


def promote(state: dict, success_file: Path) -> None:
    if not success_file.is_file():
        cleanup(state)
        raise ValueError("Candidate smoke failed; production traffic was not promoted")
    try:
        if allocation(describe(state)) != state["traffic"]:
            raise ValueError("Production traffic changed outside this release; refusing promotion")
    except DEPLOY_ERRORS:
        cleanup(state)
        raise
    try:
        set_traffic(state, {state["candidate"]: 100})
    except subprocess.CalledProcessError:
        try:
            set_traffic(state, state["traffic"])
        finally:
            cleanup(state)
        raise


def finalize(state: dict, success_file: Path) -> None:
    try:
        if not success_file.is_file():
            set_traffic(state, state["traffic"])
            raise ValueError("Production smoke failed; previous revision allocation restored")
    finally:
        cleanup(state)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "promote", "finalize"])
    parser.add_argument("--project")
    parser.add_argument("--region")
    parser.add_argument("--service")
    parser.add_argument("--lock-bucket")
    parser.add_argument("--smoke-account")
    parser.add_argument("--build-id")
    parser.add_argument("--image-file", default="/workspace/image-digest.txt")
    parser.add_argument("--success-file", type=Path)
    args = parser.parse_args()
    try:
        if args.phase == "prepare":
            prepare(args)
        else:
            if args.success_file is None:
                raise ValueError("--success-file is required")
            state = json.loads(STATE.read_text(encoding="utf-8"))
            {"promote": promote, "finalize": finalize}[args.phase](state, args.success_file)
    except DEPLOY_ERRORS as exc:
        # stdout may contain an identity token; never dump command output.
        detail = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
        parser.exit(1, f"Release phase {args.phase} failed: {detail}\n")
    print(f"Release phase {args.phase} completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
