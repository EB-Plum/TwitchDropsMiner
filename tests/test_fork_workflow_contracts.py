"""Safety contracts for the personal deployment branch, not upstream releases."""
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def workflow():
    # BaseLoader preserves YAML 1.2's `on` key instead of treating it as a boolean.
    return yaml.load((ROOT / ".github/workflows/fork-ci.yml").read_text(), Loader=yaml.BaseLoader)


def test_only_production_events_and_read_only_default():
    data = workflow()
    assert set(data["on"]) == {"push", "pull_request"}
    for event in data["on"].values():
        assert event == {"branches": ["fork/production"]}
    assert data["permissions"] == {"contents": "read"}
    assert not (ROOT / ".github/workflows/docker-ghcr.yml").exists()


def test_publication_requires_all_checks_and_exact_trusted_push():
    jobs = workflow()["jobs"]
    publish = jobs["publish"]
    assert set(publish["needs"]) == set(jobs) - {"publish"}
    assert publish["if"].split() == ["github.repository", "==", "'EB-Plum/TwitchDropsMiner'", "&&", "github.event_name", "==", "'push'", "&&", "github.ref", "==", "'refs/heads/fork/production'"]
    assert publish["permissions"] == {"contents": "read", "packages": "write"}
    for name, job in jobs.items():
        if name != "publish":
            assert job.get("permissions", {}).get("packages") != "write"
    steps = publish["steps"]
    checkout = next(step for step in steps if step["name"] == "Checkout tested commit")
    assert checkout["with"]["ref"] == "${{ github.sha }}"
    assert checkout["with"]["persist-credentials"] == "false"
    build = next(step for step in steps if step.get("id") == "image")
    assert build["with"]["push"] == "true"
    assert build["with"]["platforms"] == "linux/amd64,linux/arm64"
    tags = build["with"]["tags"].splitlines()
    assert tags == [
        "ghcr.io/eb-plum/twitch-drops-miner:sha-${{ github.sha }}-${{ github.run_id }}-${{ github.run_attempt }}",
    ]
    assert "${{ steps.image.outputs.digest }}" in str(steps)
    promote = next(step for step in steps if step["name"] == "Promote only the current production head")
    assert "refs/heads/fork/production" in promote["run"]
    assert 'if [ "$current_sha" != "$SOURCE_SHA" ]' in promote["run"]
    assert "exit 1" in promote["run"]
    assert "--tag ghcr.io/eb-plum/twitch-drops-miner:latest" in promote["run"]
    assert steps.index(promote) > steps.index(build)


def test_validation_covers_upstream_jobs_without_soft_failures():
    jobs = workflow()["jobs"]
    assert jobs["native-helper"]["uses"] == "./.github/workflows/login-helper.yml"
    assert jobs["test"]["strategy"]["matrix"]["os"] == ["ubuntu-24.04", "ubuntu-26.04"]
    commands = "\n".join(step.get("run", "") for job in jobs.values() for step in job.get("steps", []))
    for required in ["ruff check src/", "mypy src/", "python -m pytest tests/", "uv lock --check",
                     "test_validate_semver.sh", "test_github_output.sh", "test_extract_version.sh", "python -m json.tool"]:
        assert required in commands
    for job in jobs.values():
        assert job.get("continue-on-error") != "true"
        for step in job.get("steps", []):
            assert step.get("continue-on-error") != "true"
    build = next(step for step in jobs["docker"]["steps"] if step["name"] == "Build Docker image")
    assert build["with"]["push"] == "false"
    assert build["with"]["platforms"] == "linux/amd64,linux/arm64"
