from datetime import UTC, datetime
from pathlib import Path

from typer.testing import CliRunner

from mocnghe.cli import app
from mocnghe.gap import analyze_skill_gap
from mocnghe.ingestion.manual import import_jd_text_with_status
from mocnghe.models.profile import CandidateEvidence, CandidateProfile, EvidenceStatus
from mocnghe.storage.repository import CareerRepository


def test_analyze_skill_gap_detects_matches_and_gaps(tmp_path: Path) -> None:
    ws = tmp_path / "workspace"
    repo = CareerRepository(ws)
    repo.initialize()

    profile = CandidateProfile(
        profile_id="prof_gap_test",
        version="v1.0",
        confirmed_at=datetime.now(UTC),
        skills=["Python", "FastAPI", "Docker", "Git"],
        evidence=[
            CandidateEvidence(
                evidence_id="ev_py",
                status=EvidenceStatus.CANDIDATE_CONFIRMED,
                summary="Developed REST APIs with FastAPI and Python.",
                source="cv.md",
                provenance="experience",
            ),
            CandidateEvidence(
                evidence_id="ev_docker",
                status=EvidenceStatus.CANDIDATE_CONFIRMED,
                summary="Containerized microservices using Docker.",
                source="cv.md",
                provenance="experience",
            ),
        ],
    )
    repo.save_confirmed_profile(profile)

    jd_text = (
        "Title: Backend Developer\n"
        "Company: Tech Innovators\n"
        "Location: Ha Noi\n"
        "Requirements:\n"
        "- Experience in Python and FastAPI REST APIs\n"
        "- Hands-on Docker containerization\n"
        "- Experience with Kubernetes orchestration\n"
        "- 3+ years with AWS cloud architecture\n"
    )
    job, _ = import_jd_text_with_status(repo, jd_text, source_identity="synthetic_gap")

    result = analyze_skill_gap(profile, job)
    assert result.total_requirements == 4
    assert len(result.matched) >= 2
    assert len(result.gaps) >= 2

    matched_texts = [m.requirement_text for m in result.matched]
    assert any("Python" in t for t in matched_texts)
    assert any("Docker" in t for t in matched_texts)

    gap_texts = [g.requirement_text for g in result.gaps]
    assert any("Kubernetes" in t for t in gap_texts)
    assert any("AWS" in t for t in gap_texts)


def test_cli_gap_command_runs_successfully(tmp_path: Path) -> None:
    ws = tmp_path / "workspace"
    runner = CliRunner()
    runner.invoke(app, ["--workspace", str(ws), "init"])

    repo = CareerRepository(ws)
    profile = CandidateProfile(
        profile_id="prof_gap_cli",
        version="v1.0",
        confirmed_at=datetime.now(UTC),
        skills=["Python"],
        evidence=[
            CandidateEvidence(
                evidence_id="ev_py",
                status=EvidenceStatus.CANDIDATE_CONFIRMED,
                summary="Python backend engineer",
                source="cv.md",
                provenance="experience",
            )
        ],
    )
    repo.save_confirmed_profile(profile)

    job, _ = import_jd_text_with_status(
        repo,
        "Title: Python Dev\nCompany: ABC\nRequirements:\n- Python\n- Go",
        source_identity="synth",
    )

    res = runner.invoke(app, ["--workspace", str(ws), "gap", str(job.job_id)])
    assert res.exit_code == 0
    assert "Skill-Gap Analysis" in res.stdout
    assert "Python" in res.stdout
    assert "Go" in res.stdout
