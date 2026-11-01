from pathlib import Path

from mocnghe.cv import CV, Claim
from mocnghe.cv_templates import list_templates, render_template_html


def test_list_templates_returns_available_options() -> None:
    templates = list_templates()
    assert "modern" in templates
    assert "classic" in templates
    assert "minimal" in templates


def test_render_classic_template() -> None:
    cv = CV(
        id="cv_test_classic",
        profile_version="v1.0",
        profile_hash="a" * 64,
        language="en",
        identity={"name": "Alex Mercer", "email": "alex@example.com"},
        claims=[
            Claim(
                evidence_id="ev_1",
                source_quote="Built scalable data pipeline in Python.",
                text="Built scalable data pipeline in Python.",
                section="experience",
                uncertainty="low",
                status="candidate_confirmed",
            ),
            Claim(
                evidence_id="ev_2",
                source_quote="Python, Docker, SQL",
                text="Python, Docker, SQL",
                section="skills",
                uncertainty="low",
                status="candidate_confirmed",
            ),
        ],
    )

    html = render_template_html(cv, template_name="classic")
    assert "Alex Mercer" in html
    assert "alex@example.com" in html
    assert "Built scalable data pipeline in Python." in html
    assert "template-classic" in html or "classic" in html


def test_render_minimal_template() -> None:
    cv = CV(
        id="cv_test_min",
        profile_version="v1.0",
        profile_hash="a" * 64,
        language="en",
        identity={"name": "Alex Mercer"},
        claims=[
            Claim(
                evidence_id="ev_1",
                source_quote="DevOps specialist.",
                text="DevOps specialist.",
                section="experience",
                uncertainty="low",
                status="candidate_confirmed",
            )
        ],
    )

    html = render_template_html(cv, template_name="minimal")
    assert "Alex Mercer" in html
    assert "DevOps specialist." in html
    assert "minimal" in html


def test_custom_template_rendering(tmp_path: Path) -> None:
    custom_tmpl = tmp_path / "custom.html"
    custom_tmpl.write_text(
        "<html><body><h1>{{ name }}</h1><div>{{ skills }}</div></body></html>",
        encoding="utf-8",
    )

    cv = CV(
        id="cv_custom",
        profile_version="v1.0",
        profile_hash="a" * 64,
        language="en",
        identity={"name": "Custom User"},
        claims=[
            Claim(
                evidence_id="ev_1",
                source_quote="Go",
                text="Go",
                section="skills",
                uncertainty="low",
                status="candidate_confirmed",
            )
        ],
    )

    html = render_template_html(cv, custom_path=custom_tmpl)
    assert "Custom User" in html
    assert "Go" in html


def test_cli_cv_templates_command(tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from mocnghe.cli import app

    ws = tmp_path / "workspace"
    runner = CliRunner()
    runner.invoke(app, ["--workspace", str(ws), "init"])

    res = runner.invoke(app, ["--workspace", str(ws), "cv", "templates"])
    assert res.exit_code == 0
    assert "modern" in res.stdout
    assert "classic" in res.stdout
    assert "minimal" in res.stdout

