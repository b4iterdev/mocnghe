from unittest.mock import patch

from mocnghe.ingestion.batch_scanner import run_batch_crawl
from mocnghe.models.job import Job, SourceProvenance


def _dummy_job(url: str, title: str = "Test Role") -> Job:
    return Job(
        source=SourceProvenance(
            source_id="test",
            source_kind="adapter",
            original_uri=url,
        ),
        title=title,
        employer="Test Employer",
        description="Detailed description for test role",
    )


def test_batch_crawl_imported_and_existing(repo):
    urls = ["https://example.com/job1", "https://example.com/job2"]

    def mock_fetch(url, **kwargs):
        return _dummy_job(url, f"Role for {url}")

    with patch("mocnghe.ingestion.batch_scanner.fetch_job_from_url", side_effect=mock_fetch):
        report1 = run_batch_crawl(repo, urls, delay_seconds=0.0)
        assert report1.total == 2
        assert report1.imported == 2
        assert report1.existing == 0
        assert report1.failed == 0

        # Second run with same URLs -> existing
        report2 = run_batch_crawl(repo, urls, delay_seconds=0.0)
        assert report2.total == 2
        assert report2.imported == 0
        assert report2.existing == 2
        assert report2.failed == 0


def test_batch_crawl_error_resilience(repo):
    urls = ["https://example.com/good", "https://example.com/bad", "https://example.com/good2"]

    def mock_fetch(url, **kwargs):
        if "bad" in url:
            raise ConnectionError("Connection refused")
        return _dummy_job(url, f"Role for {url}")

    with patch("mocnghe.ingestion.batch_scanner.fetch_job_from_url", side_effect=mock_fetch):
        report = run_batch_crawl(repo, urls, delay_seconds=0.0)
        assert report.total == 3
        assert report.imported == 2
        assert report.failed == 1
        failed_item = next(it for it in report.items if it.status == "failed")
        assert failed_item.url == "https://example.com/bad"
        assert "Connection refused" in (failed_item.error or "")
