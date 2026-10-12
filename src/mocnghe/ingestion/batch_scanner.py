"""Batch scanner for wide automated crawling across multiple URLs and portal seeds."""
import time
from dataclasses import dataclass, field
from typing import Any

from ..models.job import hash_job_identity, job_id_from_hash
from ..storage.repository import CareerRepository
from .adapters.registry import fetch_job_from_url


@dataclass
class CrawlItemResult:
    url: str
    status: str  # "imported", "existing", "failed"
    job_id: str | None = None
    title: str | None = None
    employer: str | None = None
    error: str | None = None


@dataclass
class BatchScanReport:
    total: int = 0
    imported: int = 0
    existing: int = 0
    failed: int = 0
    items: list[CrawlItemResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "imported": self.imported,
            "existing": self.existing,
            "failed": self.failed,
            "items": [
                {
                    "url": it.url,
                    "status": it.status,
                    "job_id": it.job_id,
                    "title": it.title,
                    "employer": it.employer,
                    "error": it.error,
                }
                for it in self.items
            ],
        }


def run_batch_crawl(
    repository: CareerRepository,
    urls: list[str],
    *,
    use_browser: bool = False,
    delay_seconds: float = 0.5,
    timeout_seconds: float = 15.0,
) -> BatchScanReport:
    """
    Perform polite, bounded batch crawl across target URLs.
    Deduplicates jobs in SQLite and captures failures without terminating batch.
    """
    repository.initialize()
    report = BatchScanReport(total=len(urls))

    clean_urls = [u.strip() for u in urls if u.strip()]
    report.total = len(clean_urls)

    for i, url in enumerate(clean_urls):
        if i > 0 and delay_seconds > 0:
            time.sleep(delay_seconds)

        try:
            crawled_job = fetch_job_from_url(url, use_browser=use_browser, timeout_seconds=timeout_seconds)
            raw_content = crawled_job.freeform_text or (
                f"Tiêu đề: {crawled_job.title}\n"
                f"Công ty: {crawled_job.employer}\n"
                f"Địa điểm: {crawled_job.location}\n"
                f"{crawled_job.description}"
            )
            if crawled_job.content_hash is None or crawled_job.job_id is None:
                computed_hash = hash_job_identity(raw_content)
                crawled_job = crawled_job.model_copy(
                    update={
                        "content_hash": computed_hash,
                        "job_id": job_id_from_hash(computed_hash),
                    }
                )
            source_identity = str(crawled_job.source.original_url or crawled_job.source.original_uri)
            job, created = repository.upsert_job(
                crawled_job,
                source_identity=source_identity,
                raw_content=raw_content,
                dedupe_by_source_identity=True,
            )
            status = "imported" if created else "existing"
            if created:
                report.imported += 1
            else:
                report.existing += 1
            report.items.append(
                CrawlItemResult(
                    url=url,
                    status=status,
                    job_id=job.job_id,
                    title=job.title,
                    employer=job.employer,
                )
            )
        except (OSError, RuntimeError, ValueError) as exc:
            report.failed += 1
            report.items.append(
                CrawlItemResult(
                    url=url,
                    status="failed",
                    error=str(exc),
                )
            )

    return report
