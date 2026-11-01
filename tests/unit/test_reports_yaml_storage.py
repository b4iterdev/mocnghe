import json
from pathlib import Path

import yaml

from mocnghe.storage.repository import CareerRepository


def test_save_evaluation_report_saves_yaml_and_md(tmp_path: Path) -> None:
    ws = tmp_path / "workspace"
    repo = CareerRepository(ws)
    repo.initialize()

    report_payload = {
        "report_id": "rep_123",
        "profile_version": "v1.0",
        "job_id": "job_abc",
        "jd_content_hash": "hash123",
        "runtime": "direct_provider",
        "model": "gpt-4o",
        "recommendation": "apply",
        "fit_summary": "Strong fit for C++ and camera systems.",
    }

    repo.save_evaluation_report(
        report_id="rep_123",
        profile_version="v1.0",
        job_id="job_abc",
        jd_content_hash="hash123",
        runtime="direct_provider",
        model="gpt-4o",
        payload_json=json.dumps(report_payload),
    )

    yaml_file = ws / "reports" / "rep_123.yaml"
    md_file = ws / "reports" / "rep_123.md"

    assert yaml_file.exists()
    assert md_file.exists()

    data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
    assert data["report_id"] == "rep_123"
    assert data["model"] == "gpt-4o"
    assert data["recommendation"] == "apply"

    md_text = md_file.read_text(encoding="utf-8")
    assert "rep_123" in md_text
    assert "Strong fit for C++ and camera systems." in md_text

    assert repo.count_evaluation_reports() == 1
    doc = repo.doctor()
    assert doc["evaluation_reports"] == "1"
