from datetime import UTC, datetime
from pathlib import Path

import yaml

from mocnghe.applications.tracker import ApplicationTracker
from mocnghe.cv import CVService
from mocnghe.ingestion.manual import import_jd_text_with_status
from mocnghe.models.profile import CandidateEvidence, CandidateProfile, EvidenceStatus
from mocnghe.storage.repository import CareerRepository


def test_tracker_writes_yaml_and_pipeline_md(tmp_path: Path) -> None:
    ws = tmp_path / "workspace"
    repo = CareerRepository(ws)
    repo.initialize()

    # Create profile
    profile = CandidateProfile(
        profile_id="prof_track",
        version="v1",
        confirmed_at=datetime(2026, 10, 1, tzinfo=UTC),
        evidence=[
            CandidateEvidence(
                evidence_id="ev1",
                status=EvidenceStatus.CANDIDATE_CONFIRMED,
                source="cv.md",
                summary="DevOps experience",
                provenance="experience",
            )
        ],
    )
    repo.save_confirmed_profile(profile)

    # Import job
    job, _ = import_jd_text_with_status(
        repo,
        "Title: DevOps Engineer\nEmployer: Tech Corp\nLocation: Ha Noi",
        source_identity="synthetic",
    )

    # 1. Check initial YAML created on discovery
    yaml_file = ws / "applications" / f"{job.job_id}.yaml"
    assert yaml_file.exists()
    init_data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
    assert init_data["job_id"] == job.job_id
    assert init_data["state"] == "discovered"

    # 2. Transition to shortlisted
    tracker = ApplicationTracker(repo)
    tracker.transition(job.job_id, "shortlisted")

    assert yaml_file.exists()
    short_data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
    assert short_data["state"] == "shortlisted"

    pipeline_md = ws / "pipeline.md"
    assert pipeline_md.exists()
    pipeline_text = pipeline_md.read_text(encoding="utf-8")
    assert "DevOps Engineer" in pipeline_text
    assert str(job.job_id) in pipeline_text

    # 3. Transition to drafting -> ready -> applied with CV
    cvs = CVService(repo)
    cv = cvs.create("v1", ["ev1"], language="en", job_id=job.job_id)
    cvs.approve(cv.id, cvs.content_hash(cv))

    tracker.transition(job.job_id, "drafting")
    tracker.transition(job.job_id, "ready", cv_id=cv.id)
    tracker.transition(job.job_id, "applied", cv_id=cv.id, confirm=True)

    applied_data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
    assert applied_data["state"] == "applied"
    assert applied_data["cv_version"] == cv.id
    assert applied_data["applied_at"] is not None
    assert len(applied_data["events"]) == 4

    # Pipeline contains applied section
    updated_pipeline = pipeline_md.read_text(encoding="utf-8")
    assert "## Applied" in updated_pipeline
    assert str(job.job_id) in updated_pipeline
