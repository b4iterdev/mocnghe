from datetime import UTC, datetime
from pathlib import Path

from typer.testing import CliRunner

from mocnghe.briefing import export_framing_bundle, generate_brief, generate_framing
from mocnghe.cli import app
from mocnghe.models.profile import (
    CandidateEvidence,
    CandidateProfile,
    CompensationFloor,
    EvidenceStatus,
    RankedTarget,
    WorkPreferences,
)
from mocnghe.storage.repository import CareerRepository


def _make_test_profile() -> CandidateProfile:
    return CandidateProfile(
        profile_id="prof_brief_test",
        version="v1.0",
        confirmed_at=datetime.now(UTC),
        identity={"name": "Nguyen Minh Thai", "email": "thai@example.com"},
        ranked_targets=[
            RankedTarget(rank=1, title="DevOps Engineer", occupation_family="infrastructure"),
            RankedTarget(rank=2, title="Backend Developer", occupation_family="software"),
        ],
        preferences=WorkPreferences(
            preferred_locations=["Ha Noi"],
            remote_from_vietnam=True,
            wants_full_time=True,
            wants_internship=True,
            industry_exclusions=["gambling", "crypto"],
            full_time_compensation_floor=CompensationFloor(
                amount=15_000_000,
                currency="VND",
                period="month",
                gross_net="gross",
            ),
            internship_compensation_floor=CompensationFloor(
                amount=6_000_000,
                currency="VND",
                period="month",
                gross_net="gross",
            ),
        ),
        skills=["Python", "Docker", "Kubernetes", "Linux"],
        evidence=[
            CandidateEvidence(
                evidence_id="ev_devops_1",
                status=EvidenceStatus.CANDIDATE_CONFIRMED,
                summary="Maintained Kubernetes clusters and Flux v2 GitOps pipelines.",
                source="cv.md",
                source_quote="Maintained Kubernetes clusters and Flux v2 GitOps pipelines.",
                provenance="experience",
            )
        ],
    )


def test_generate_brief_contains_triage_boundaries() -> None:
    profile = _make_test_profile()
    brief_md = generate_brief(profile)

    assert "First-Pass Triage Brief" in brief_md
    assert "DevOps Engineer" in brief_md
    assert "15,000,000 VND / month" in brief_md
    assert "6,000,000 VND / month" in brief_md
    assert "Ha Noi" in brief_md
    assert "gambling" in brief_md


def test_generate_framing_contains_proof_mappings_and_caveats() -> None:
    profile = _make_test_profile()
    framing_md = generate_framing(profile)

    assert "Role Framing & Proof Mapping" in framing_md
    assert "DevOps Engineer" in framing_md
    assert "ev_devops_1" in framing_md
    assert "Kubernetes clusters and Flux v2" in framing_md
    assert "Factual Caveats & Guardrails" in framing_md


def test_export_framing_bundle_and_cli(tmp_path: Path) -> None:
    ws = tmp_path / "workspace"
    repo = CareerRepository(ws)
    repo.initialize()
    profile = _make_test_profile()
    repo.save_confirmed_profile(profile)

    bundle = export_framing_bundle(profile, ws)
    assert bundle["brief"].exists()
    assert bundle["profile"].exists()

    runner = CliRunner()
    res = runner.invoke(app, ["--workspace", str(ws), "profile", "brief"])
    assert res.exit_code == 0
    assert "First-Pass Triage Brief" in res.stdout
    assert "DevOps Engineer" in res.stdout

    res2 = runner.invoke(app, ["--workspace", str(ws), "profile", "framing"])
    assert res2.exit_code == 0
    assert "Exported framing bundle" in res2.stdout
