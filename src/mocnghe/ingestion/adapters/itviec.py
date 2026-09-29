from __future__ import annotations

from datetime import UTC, datetime

from bs4 import BeautifulSoup

from ...models.job import Job, SourceProvenance, hash_job_identity, job_id_from_hash
from ..itviec import _looks_like_challenge, _parse_detail
from .base import BaseJobAdapter


class ITviecAdapter(BaseJobAdapter):
    """Adapter for ITviec job postings (itviec.com)."""

    name = "itviec"
    domains = ("itviec.com",)

    def parse_job(self, content: str, *, url: str) -> Job:
        if _looks_like_challenge(content):
            raise RuntimeError("ITviec page returned Cloudflare challenge / bot-block.")

        soup = BeautifulSoup(content, "html.parser")

        # Reuse robust ITviec detail parsing logic if valid
        detail_job = _parse_detail(
            content,
            fallback_title="",
            detail_url=url,
            retrieved_at=datetime.now(UTC),
            source_kind="itviec",
        )
        if detail_job is not None:
            # Build freeform_text for structured requirements extraction
            freeform_lines = [
                f"Title: {detail_job.title}",
                f"Company: {detail_job.employer}",
                f"Location: {detail_job.location}",
                f"URL: {url}",
                "",
                "Description:",
                detail_job.description,
                "",
                "Yêu cầu:",
                detail_job.requirements,
            ]
            if detail_job.benefits:
                freeform_lines.extend(["", "Quyền lợi:", detail_job.benefits])

            freeform_text = "\n".join(freeform_lines)
            content_hash = hash_job_identity(freeform_text)
            return detail_job.model_copy(
                update={
                    "job_id": job_id_from_hash(content_hash),
                    "content_hash": content_hash,
                    "freeform_text": freeform_text,
                }
            )

        # Fallback parsing if _parse_detail missed specific layout nuances
        title_el = soup.find("h1")
        title = title_el.get_text(strip=True) if title_el else "Unknown IT Role"

        employer_el = soup.select_one("a[href*='/companies/'], .company-name, [class*='company']")
        employer = employer_el.get_text(strip=True) if employer_el else "ITviec Employer"

        loc_el = soup.select_one(".location, [class*='location'], .address")
        location = loc_el.get_text(strip=True) if loc_el else "Vietnam"

        body_el = soup.find("article") or soup.find("main") or soup.body
        body_text = body_el.get_text(separator="\n", strip=True) if body_el else content[:5000]

        freeform_lines = [
            f"Title: {title}",
            f"Company: {employer}",
            f"Location: {location}",
            f"URL: {url}",
            "",
            body_text,
        ]
        freeform_text = "\n".join(freeform_lines)
        content_hash = hash_job_identity(freeform_text)

        source = SourceProvenance.model_validate(
            {
                "source_id": f"itviec:{url}",
                "source_kind": "itviec",
                "original_uri": url,
                "original_url": url,
                "retrieved_at": datetime.now(UTC),
            }
        )

        return Job(
            job_id=job_id_from_hash(content_hash),
            content_hash=content_hash,
            source=source,
            title=title,
            employer=employer,
            location=location,
            description=body_text[:1000] if body_text else title,
            requirements="unknown",
            freeform_text=freeform_text,
        )
