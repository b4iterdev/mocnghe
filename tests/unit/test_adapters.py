"""Unit tests for the modular job adapter system."""

import pytest

from mocnghe.ingestion.adapters.generic import GenericAdapter
from mocnghe.ingestion.adapters.greenhouse import GreenhouseAdapter
from mocnghe.ingestion.adapters.indeed import IndeedAdapter
from mocnghe.ingestion.adapters.itviec import ITviecAdapter
from mocnghe.ingestion.adapters.registry import find_adapter

SAMPLE_GREENHOUSE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Software Engineer (Intern, C#) at Constructor TECH</title>
    <meta property="og:title" content="Software Engineer (Intern, C#)">
</head>
<body>
    <div class="job__header">
        <h1 class="app-title">Software Engineer (Intern, C#)</h1>
        <span class="company-name">Constructor TECH</span>
        <div class="location">Bremen, Germany</div>
    </div>
    <div id="content">
        <p>Our mission is to enable all educational organisations...</p>
        <h2>Required Qualifications:</h2>
        <ul>
            <li>Current Computer Science student</li>
            <li>Experience with C# or C++</li>
        </ul>
        <h2>Good to Have:</h2>
        <ul>
            <li>Basic knowledge of RESTful APIs</li>
        </ul>
    </div>
</body>
</html>
"""

SAMPLE_ITVIEC_HTML = """
<!DOCTYPE html>
<html>
<body>
    <div class="job-details">
        <h1>Senior Backend Engineer (Python / Go)</h1>
        <a href="/companies/vietnam-tech-corp" class="employer-name">Vietnam Tech Corp</a>
        <div class="location">Hà Nội</div>
        <h2>Job description</h2>
        <p>Develop high scale distributed systems.</p>
        <h2>Your skills and experience</h2>
        <ul>
            <li>3+ years Python experience</li>
            <li>Experience with PostgreSQL</li>
        </ul>
        <h2>Why you'll love working here</h2>
        <p>13th month salary, MacBooks provided.</p>
    </div>
</body>
</html>
"""

SAMPLE_INDEED_HTML = """
<!DOCTYPE html>
<html>
<head>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "JobPosting",
        "title": "Full Stack Developer",
        "hiringOrganization": {
            "@type": "Organization",
            "name": "Global Software Ltd"
        },
        "jobLocation": {
            "@type": "Place",
            "address": {
                "@type": "PostalAddress",
                "addressLocality": "Singapore",
                "addressCountry": "SG"
            }
        },
        "description": "<p>We are seeking a Full Stack Developer with React and Node.js skills.</p>"
    }
    </script>
</head>
<body>
    <h1 class="jobsearch-JobInfoHeader-title">Full Stack Developer</h1>
</body>
</html>
"""


def test_greenhouse_adapter_matches_domains():
    adapter = GreenhouseAdapter()
    assert adapter.supports_url("https://job-boards.eu.greenhouse.io/constructortech/jobs/4772061101")
    assert adapter.supports_url("https://boards.greenhouse.io/airbnb/jobs/12345")
    assert not adapter.supports_url("https://itviec.com/it-jobs/c-sharp")


def test_greenhouse_adapter_parses_html():
    adapter = GreenhouseAdapter()
    url = "https://job-boards.eu.greenhouse.io/constructortech/jobs/4772061101"
    job = adapter.parse_job(SAMPLE_GREENHOUSE_HTML, url=url)

    assert job.title == "Software Engineer (Intern, C#)"
    assert "Constructor" in job.employer
    assert "Bremen" in job.location
    assert "Current Computer Science student" in job.requirements or "Current Computer Science student" in job.freeform_text
    assert str(job.source.original_url) == url
    assert job.source.source_kind == "greenhouse"


def test_itviec_adapter():
    adapter = ITviecAdapter()
    url = "https://itviec.com/it-jobs/senior-backend-engineer-vietnam-tech-corp"
    assert adapter.supports_url(url)
    assert not adapter.supports_url("https://indeed.com/viewjob?jk=123")

    job = adapter.parse_job(SAMPLE_ITVIEC_HTML, url=url)
    assert "Backend Engineer" in job.title
    assert "Vietnam Tech Corp" in job.employer
    assert "Hà Nội" in job.location
    assert "Python" in job.requirements
    assert job.source.source_kind == "itviec"


def test_indeed_adapter_with_jsonld():
    adapter = IndeedAdapter()
    url = "https://www.indeed.com/viewjob?jk=abcdef123456"
    assert adapter.supports_url(url)
    assert not adapter.supports_url("https://itviec.com")

    job = adapter.parse_job(SAMPLE_INDEED_HTML, url=url)
    assert job.title == "Full Stack Developer"
    assert job.employer == "Global Software Ltd"
    assert "Singapore" in job.location
    assert "React" in job.description or "React" in job.freeform_text
    assert job.source.source_kind == "indeed"


def test_generic_adapter_fallback():
    html = """
    <html>
    <head><title>Senior Python Dev at TechCorp</title></head>
    <body>
        <h1>Senior Python Dev</h1>
        <p>We are TechCorp looking for a Python engineer.</p>
    </body>
    </html>
    """
    adapter = GenericAdapter()
    url = "https://example.com/jobs/1"
    assert adapter.supports_url(url)
    job = adapter.parse_job(html, url=url)
    assert "Python" in job.title
    assert job.source.original_uri == url


def test_registry_finds_specific_adapter_then_generic():
    gh_adapter = find_adapter("https://job-boards.eu.greenhouse.io/test/jobs/123")
    assert isinstance(gh_adapter, GreenhouseAdapter)

    it_adapter = find_adapter("https://itviec.com/it-jobs/ruby-dev")
    assert isinstance(it_adapter, ITviecAdapter)

    in_adapter = find_adapter("https://vn.indeed.com/viewjob?jk=987654")
    assert isinstance(in_adapter, IndeedAdapter)

    gen_adapter = find_adapter("https://unknown-startup.io/careers/456")
    assert isinstance(gen_adapter, GenericAdapter)


def test_browser_not_installed_error_message(monkeypatch):
    """When playwright is not installed, clear actionable error is raised."""
    # Simulate playwright not importable
    import sys

    from mocnghe.ingestion.adapters.browser import fetch_rendered_html
    monkeypatch.setitem(sys.modules, "playwright", None)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", None)

    with pytest.raises(RuntimeError, match="mocnghe\\[browser\\]"):
        fetch_rendered_html("https://example.com")
