from pathlib import Path

import yaml

from mocnghe.ingestion.manual import import_jd_text_with_status
from mocnghe.storage.repository import CareerRepository


def test_import_job_writes_markdown_with_yaml_frontmatter(tmp_path: Path) -> None:
    ws = tmp_path / "workspace"
    repo = CareerRepository(ws)
    repo.initialize()

    jd_text = (
        "Title: Senior Rust Engineer\n"
        "Company: Global Systems\n"
        "Location: Ha Noi\n"
        "Requirements:\n"
        "- 3+ years Rust\n"
        "- Concurrency experience\n"
    )
    job, is_new = import_jd_text_with_status(repo, jd_text, source_identity="synthetic_rust")
    assert is_new is True

    job_file = ws / "jobs" / f"{job.job_id}.md"
    assert job_file.exists()

    content = job_file.read_text(encoding="utf-8")
    assert content.startswith("---")
    parts = content.split("---", 2)
    assert len(parts) >= 3

    fm = yaml.safe_load(parts[1])
    assert fm["job_id"] == job.job_id
    assert fm["title"] == "Senior Rust Engineer"
    assert fm["employer"] == "Global Systems"
    assert fm["content_hash"] == job.content_hash

    # Check Markdown body
    assert "# Senior Rust Engineer — Global Systems" in parts[2]
    assert "3+ years Rust" in parts[2]

    # Verify retrieval
    assert job.job_id is not None
    retrieved = repo.get_job(job.job_id)
    assert retrieved is not None
    assert retrieved.title == "Senior Rust Engineer"
    assert retrieved.job_id == job.job_id
