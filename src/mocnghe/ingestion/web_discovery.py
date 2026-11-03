from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qs, unquote, urlparse

import httpx


@dataclass
class DiscoveredLink:
    title: str
    url: str
    snippet: str
    source_domain: str


# Common supported hiring platforms for high signal extraction
DEFAULT_TARGET_DOMAINS = (
    "itviec.com",
    "vietnamworks.com",
    "greenhouse.io",
    "indeed.com",
    "topcv.vn",
    "careerbuilder.vn",
)


def _clean_duckduckgo_url(raw_url: str) -> str:
    """Extract destination URL from DuckDuckGo redirect link."""
    if "/l/?" in raw_url or "duckduckgo.com/l/" in raw_url:
        parsed = urlparse(raw_url)
        params = parse_qs(parsed.query)
        if "uddg" in params:
            return unquote(params["uddg"][0])
    return raw_url


def search_public_jobs(
    query: str,
    *,
    location: str | None = None,
    limit: int = 5,
    timeout_seconds: float = 10.0,
    client: httpx.Client | None = None,
) -> list[DiscoveredLink]:
    """Search public web for job postings via DuckDuckGo HTML endpoint without API keys."""
    full_query = f"{query} việc làm job tuyển dụng"
    if location:
        full_query += f" {location}"

    # Target key job boards or direct postings
    domains_filter = " OR ".join(f"site:{d}" for d in DEFAULT_TARGET_DOMAINS[:4])
    search_terms = f"{full_query} ({domains_filter})"

    url = "https://html.duckduckgo.com/html/"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    data = {"q": search_terms}

    try:
        if client is not None:
            res = client.post(url, data=data, headers=headers, timeout=timeout_seconds)
        else:
            with httpx.Client(timeout=timeout_seconds, follow_redirects=True) as local_client:
                res = local_client.post(url, data=data, headers=headers)
        if res.status_code != 200:
            return []
        html = res.text
    except (httpx.HTTPError, OSError):
        return []

    return parse_duckduckgo_results(html, limit=limit)


def parse_duckduckgo_results(html: str, *, limit: int = 5) -> list[DiscoveredLink]:
    """Parse DuckDuckGo HTML search results page."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    results: list[DiscoveredLink] = []
    seen_urls: set[str] = set()

    # DuckDuckGo HTML layout uses .result or .web-result
    elements = soup.select(".result") or soup.select(".web-result")
    for el in elements:
        title_el = el.select_one(".result__a") or el.select_one("a.result__url")
        snippet_el = el.select_one(".result__snippet")

        if not title_el:
            continue

        raw_url = str(title_el.get("href", ""))
        clean_url = _clean_duckduckgo_url(raw_url)
        if not clean_url or not clean_url.startswith("http"):
            continue

        domain = (urlparse(clean_url).hostname or "").lower()
        if clean_url in seen_urls:
            continue
        seen_urls.add(clean_url)

        title = title_el.get_text(strip=True)
        snippet = snippet_el.get_text(strip=True) if snippet_el else ""

        results.append(
            DiscoveredLink(
                title=title,
                url=clean_url,
                snippet=snippet,
                source_domain=domain,
            )
        )
        if len(results) >= limit:
            break

    return results
