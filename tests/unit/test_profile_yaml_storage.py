from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from mocnghe.cli import app
from mocnghe.models.profile import CandidateEvidence, CandidateProfile, EvidenceStatus
from mocnghe.storage.repository import CareerRepository


def test_repository_saves_and_loads_draft_as_yaml(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    repo = CareerRepository(ws)
    repo.initialize()

    repo.save_profile_draft("draft-123", {"field1": {"text": "hello", "answered_by": "tester"}})

    draft_file = ws / "drafts" / "draft-123.yaml"
    assert draft_file.exists()
    content = yaml.safe_load(draft_file.read_text(encoding="utf-8"))
    assert content["field1"]["text"] == "hello"

    loaded = repo.load_profile_draft("draft-123")
    assert loaded == {"field1": {"text": "hello", "answered_by": "tester"}}


def test_repository_saves_and_loads_confirmed_profile_as_yaml_and_md(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    repo = CareerRepository(ws)
    repo.initialize()

    profile = CandidateProfile(
        profile_id="prof_yaml_1",
        version="1.0",
        confirmed_at=datetime.now(UTC),
        evidence=[
            CandidateEvidence(
                evidence_id="ev_1",
                status=EvidenceStatus.CANDIDATE_CONFIRMED,
                summary="Built Python system",
                source="profile.yaml",
            )
        ],
    )

    repo.save_confirmed_profile(profile)

    yaml_file = ws / "profiles" / "1.0.yaml"
    md_file = ws / "profiles" / "1.0.md"
    assert yaml_file.exists()
    assert md_file.exists()

    # Immutable
    with pytest.raises(ValueError, match="immutable"):
        repo.save_confirmed_profile(profile)

    # Retrieval
    retrieved = repo.get_profile_version("1.0")
    assert retrieved is not None
    assert retrieved.profile_id == "prof_yaml_1"
    assert retrieved.evidence[0].evidence_id == "ev_1"

    latest = repo.get_latest_profile()
    assert latest is not None
    assert latest.profile_id == "prof_yaml_1"


def test_cli_profile_validation_and_confirm_file_supports_yaml(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    runner = CliRunner()
    runner.invoke(app, ["--workspace", str(ws), "init"])

    profile_data = {
        "profile_id": "test_yaml_cli",
        "version": "1.0",
        "evidence": [
            {
                "evidence_id": "ev_yaml_1",
                "status": "candidate_confirmed",
                "summary": "YAML profile evidence",
                "source": "profile.yaml",
            }
        ],
    }

    yaml_path = ws / "profile.yaml"
    yaml_path.write_text(yaml.safe_dump(profile_data), encoding="utf-8")

    # Validate
    val_res = runner.invoke(app, ["--workspace", str(ws), "profile", "validation"])
    assert val_res.exit_code == 0
    assert "test_yaml_cli" in val_res.stdout

    # Confirm-file
    conf_res = runner.invoke(app, ["--workspace", str(ws), "profile", "confirm-file"])
    assert conf_res.exit_code == 0
    assert "test_yaml_cli" in conf_res.stdout
    assert "1.0" in conf_res.stdout

    repo = CareerRepository(ws)
    latest = repo.get_latest_profile()
    assert latest is not None
    assert latest.profile_id == "test_yaml_cli"
