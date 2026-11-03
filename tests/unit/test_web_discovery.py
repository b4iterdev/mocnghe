from unittest.mock import MagicMock

from mocnghe.ingestion.web_discovery import (
    _clean_duckduckgo_url,
    parse_duckduckgo_results,
    search_public_jobs,
)


def test_clean_duckduckgo_url():
    raw = "https://duckduckgo.com/l/?uddg=https%3A%2F%2Fitviec.com%2Fit-jobs%2Fpython-dev&rut=123"
    assert _clean_duckduckgo_url(raw) == "https://itviec.com/it-jobs/python-dev"

    direct = "https://vietnamworks.com/job-123"
    assert _clean_duckduckgo_url(direct) == direct


def test_parse_duckduckgo_results():
    sample_html = """
    <div class="result">
        <a class="result__a" href="https://duckduckgo.com/l/?uddg=https%3A%2F%2Fitviec.com%2Fjob%2Fpython-lead">Senior Python Developer</a>
        <div class="result__snippet">Great python job in Hanoi with attractive benefits</div>
    </div>
    <div class="result">
        <a class="result__a" href="https://vietnamworks.com/job/backend-engineer">Backend Engineer</a>
        <div class="result__snippet">Work with FastAPI and Docker</div>
    </div>
    """
    results = parse_duckduckgo_results(sample_html, limit=5)
    assert len(results) == 2
    assert results[0].title == "Senior Python Developer"
    assert results[0].url == "https://itviec.com/job/python-lead"
    assert results[0].source_domain == "itviec.com"
    assert "Hanoi" in results[0].snippet


def test_search_public_jobs_mock():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = """
    <div class="result">
        <a class="result__a" href="https://itviec.com/job/1">Dev Job</a>
        <div class="result__snippet">Snippet</div>
    </div>
    """
    mock_client = MagicMock()
    mock_client.post.return_value = mock_resp

    results = search_public_jobs("python", location="Hanoi", client=mock_client)
    assert len(results) == 1
    assert results[0].url == "https://itviec.com/job/1"
