"""Cover letter CLI commands."""
import json
from pathlib import Path
from typing import Annotated

import typer

from .cover_letter import CoverLetterService
from .cv import CVService
from .cv_cli import guarded

cover_letter_app = typer.Typer(no_args_is_help=True)


def service(ctx: typer.Context) -> CoverLetterService:
    repo = ctx.obj["repository"]
    return CoverLetterService(CVService(repo))


@cover_letter_app.command("create")
@guarded
def create(
    ctx: typer.Context,
    cv_id: Annotated[str, typer.Option("--cv-id", help="Approved CV ID")],
    job_id: Annotated[str, typer.Option("--job-id", help="Target Job ID")],
    recipient: Annotated[str | None, typer.Option("--recipient", help="Hiring team or contact")] = None,
    opening: Annotated[str | None, typer.Option("--opening", help="Custom opening statement")] = None,
    closing: Annotated[str | None, typer.Option("--closing", help="Custom closing statement")] = None,
):
    """Create a structured cover letter grounded in approved CV claims."""
    s = service(ctx)
    cl = s.create(cv_id, job_id, recipient=recipient, custom_opening=opening, custom_closing=closing)
    typer.echo(cl.model_dump_json(indent=2))


@cover_letter_app.command("review")
@guarded
def review(ctx: typer.Context, cl_id: str):
    """Review cover letter content, approval status, and content hash."""
    s = service(ctx)
    cl = s.get(cl_id)
    typer.echo(
        json.dumps(
            {
                "cover_letter": cl.model_dump(mode="json"),
                "content_hash": s.content_hash(cl),
                "approved": s.approved(cl_id),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


@cover_letter_app.command("approve")
@guarded
def approve(
    ctx: typer.Context,
    cl_id: str,
    content_hash: Annotated[str, typer.Option("--hash", help="Exact hash from review")],
):
    """Approve exact cover letter content before export."""
    s = service(ctx)
    s.approve(cl_id, content_hash)
    typer.echo("Approved reviewed cover letter content; not submitted.")


@cover_letter_app.command("export")
@guarded
def export(
    ctx: typer.Context,
    cl_id: str,
    output: Annotated[Path, typer.Option("--output", help="Target bundle directory")],
    max_pages: Annotated[int, typer.Option("--max-pages", min=1, max=3)] = 1,
):
    """Export approved cover letter as markdown, text, and PDF bundle."""
    s = service(ctx)
    s.export(cl_id, output, max_pages=max_pages)
    typer.echo(f"Exported cover letter bundle: {output}")
