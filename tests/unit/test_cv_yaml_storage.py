from datetime import UTC, datetime
from pathlib import Path

import yaml

from mocnghe.cv import CVService
from mocnghe.models.profile import CandidateEvidence, CandidateProfile, EvidenceStatus
from mocnghe.storage.repository import CareerRepository


def test_cv_service_saves_yaml_and_md(tmp_path: Path) -> None:
    ws = tmp_path / "workspace"
    repo = CareerRepository(ws)
    repo.initialize()

    profile = CandidateProfile(
        profile_id="prof_cv_test",
        version="v1",
        confirmed_at=datetime.now(UTC),
        identity={"name": "Nguyen Van A", "email": "a@example.com"},
        evidence=[
            CandidateEvidence(
                evidence_id="ev_exp_1",
                status=EvidenceStatus.CANDIDATE_CONFIRMED,
                summary="Led backend project in Python.",
                source="cv.md",
                source_quote="Led backend project in Python.",
                provenance="experience",
            )
        ],
    )
    repo.save_confirmed_profile(profile)

    service = CVService(repo)
    cv = service.create("v1", ["ev_exp_1"], language="en", identity_keys=["name", "email"])

    cv_yaml = ws / "cvs" / f"{cv.id}.yaml"
    cv_md = ws / "cvs" / f"{cv.id}.md"

    assert cv_yaml.exists()
    assert cv_md.exists()

    data = yaml.safe_load(cv_yaml.read_text(encoding="utf-8"))
    assert data["id"] == cv.id
    assert data["profile_version"] == "v1"

    md_text = cv_md.read_text(encoding="utf-8")
    assert "Nguyen Van A" in md_text
    assert "Led backend project in Python." in md_text

    # Approval YAML
    content_hash = service.content_hash(cv)
    service.approve(cv.id, content_hash)

    approval_yaml = ws / "cvs" / f"{cv.id}.approval.yaml"
    assert approval_yaml.exists()
    appr_data = yaml.safe_load(approval_yaml.read_text(encoding="utf-8"))
    assert appr_data["content_hash"] == content_hash

    assert service.approved(cv.id) is True
