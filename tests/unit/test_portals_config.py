from pathlib import Path

import yaml

from mocnghe.models.job import (
    EmploymentType,
    Job,
    Salary,
    SalaryKind,
    SourceProvenance,
)
from mocnghe.portals import filter_job, load_portals_config, validate_portals_config


def test_validate_and_load_portals_yaml(tmp_path: Path) -> None:
    ws = tmp_path / "workspace"
    ws.mkdir(parents=True)
    portals_file = ws / "portals.yaml"

    sample_config = {
        "title_filter": {
            "positive": ["Python", "Backend", "DevOps"],
            "negative": ["Senior", "Lead", "Manager"],
        },
        "location_filter": {
            "allow": ["Ha Noi", "Remote"],
            "negative": ["Ho Chi Minh"],
        },
        "content_filter": {
            "negative": ["gambling", "casino"],
        },
        "sources": [
            {
                "name": "itviec",
                "urls": ["https://itviec.com/it-jobs/python/ha-noi"],
                "enabled": True,
            }
        ],
    }
    portals_file.write_text(yaml.safe_dump(sample_config), encoding="utf-8")

    errors = validate_portals_config(portals_file)
    assert errors == []

    config = load_portals_config(ws)
    assert config is not None
    assert "Python" in config.title_filter.positive
    assert "Senior" in config.title_filter.negative
    assert len(config.sources) == 1


def test_filter_job_accepts_and_rejects(tmp_path: Path) -> None:
    ws = tmp_path / "workspace"
    ws.mkdir(parents=True)
    portals_file = ws / "portals.yaml"
    portals_file.write_text(
        yaml.safe_dump({
            "title_filter": {
                "positive": ["Python", "Backend"],
                "negative": ["Senior", "Lead"],
            },
            "location_filter": {
                "allow": ["Ha Noi", "Remote"],
                "negative": ["Da Nang"],
            },
            "content_filter": {
                "negative": ["gambling"],
            },
        }),
        encoding="utf-8",
    )
    config = load_portals_config(ws)
    assert config is not None

    source = SourceProvenance(
        source_id="src_test",
        source_kind="http_search",
        original_uri="https://test.com",
    )
    salary = Salary(kind=SalaryKind.UNKNOWN)

    # 1. Matching job
    good_job = Job(
        job_id="job_good",
        content_hash="a" * 64,
        source=source,
        title="Junior Python Backend Engineer",
        employer="ACME",
        location="Ha Noi",
        workplace_policy="hybrid",
        employment_type=EmploymentType.FULL_TIME,
        salary=salary,
        description="Build Python microservices.",
        requirements="Python, Docker",
        benefits="Good pay",
        freeform_text="Standard tech job",
    )
    keep, reason = filter_job(config, good_job)
    assert keep is True
    assert reason is None

    # 2. Excluded by negative title filter
    senior_job = good_job.model_copy(update={"title": "Senior Python Backend Engineer"})
    keep, reason = filter_job(config, senior_job)
    assert keep is False
    assert reason is not None
    assert "Senior" in reason

    # 3. Excluded by positive title filter (no positive matches)
    sales_job = good_job.model_copy(update={"title": "Product Marketing Lead"})
    keep, reason = filter_job(config, sales_job)
    assert keep is False
    assert reason is not None

    # 4. Excluded by location filter
    danang_job = good_job.model_copy(update={"location": "Da Nang"})
    keep, reason = filter_job(config, danang_job)
    assert keep is False
    assert reason is not None
    assert "location" in reason.lower()

    # 5. Excluded by content filter
    gambling_job = good_job.model_copy(update={"description": "Online gambling platform developer."})
    keep, reason = filter_job(config, gambling_job)
    assert keep is False
    assert reason is not None
    assert "gambling" in reason.lower()


def test_cli_portals_validate(tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from mocnghe.cli import app

    ws = tmp_path / "workspace"
    runner = CliRunner()
    runner.invoke(app, ["--workspace", str(ws), "init"])

    # Missing portals.yaml
    res_missing = runner.invoke(app, ["--workspace", str(ws), "portals", "validate"])
    assert res_missing.exit_code != 0

    # Valid portals.yaml
    portals_path = ws / "portals.yaml"
    portals_path.write_text(yaml.safe_dump({"title_filter": {"positive": ["Python"]}}), encoding="utf-8")
    res_valid = runner.invoke(app, ["--workspace", str(ws), "portals", "validate"])
    assert res_valid.exit_code == 0
    assert "portals: valid" in res_valid.stdout

