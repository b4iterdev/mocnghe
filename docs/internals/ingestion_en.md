# Ingestion Subsystem

The `ingestion` subsystem ingests job descriptions (JDs) from heterogeneous sources (plain text files, standard input, public HTTP APIs, and headless browser rendering), normalizes them into a unified `Job` model, and binds full provenance metadata (`SourceProvenance`).

---

## 1. High-Level Architecture

```
                 +-----------------------------------------------+
                 |                 Input Sources                 |
                 |     Web URLs / Text files / Stdin / Fixtures  |
                 +-----------------------+-----------------------+
                                         |
                                         v
                         +-------------------------------+
                         |      Registry (registry.py)   |
                         |   find_adapter(url) -> Adapter|
                         +---------------+---------------+
                                         |
         +-------------------------------+-------------------------------+
         |                               |                               |
         v                               v                               v
[ GreenhouseAdapter ]            [ ITviecAdapter ]               [ IndeedAdapter ]
  - Domain matching               - Challenge detection           - JSON-LD Schema
  - DOM selector parsing          - Section splitting             - window._initialData
         |                               |                               |
         +-------------------------------+-------------------------------+
                                         | (fallback on unknown domains)
                                         v
                                 [ GenericAdapter ]
                                  - OpenGraph / Meta
                                  - Semantic HTML
                                         |
                                         v
                 +-----------------------------------------------+
                 |                Fetch Mechanism                |
                 |  - Static HTTP: httpx.Client (with UA)        |
                 |  - Dynamic: Playwright headless browser       |
                 +-----------------------+-----------------------+
                                         |
                                         v
                 +-----------------------------------------------+
                 |          Normalization & Fingerprinting       |
                 |  - freeform_text aggregation                  |
                 |  - hash_job_identity() -> SHA-256             |
                 |  - job_id_from_hash() -> "job_<16 hex>"       |
                 +-----------------------+-----------------------+
                                         |
                                         v
                         CareerRepository.upsert_job()
```

---

## 2. Component Breakdown

### 2.1. `BaseJobAdapter` (`adapters/base.py`)
All site-specific adapters implement this abstract contract:
- `name: str`: Adapter identifier (e.g. `"greenhouse"`, `"itviec"`).
- `domains: tuple[str, ...]`: Handled domain patterns. If empty, the adapter acts as a catch-all fallback.
- `supports_url(url: str) -> bool`: Validates if a target URL matches the configured domain patterns.
- `parse_job(content: str, *, url: str) -> Job`: Pure parsing routine converting raw HTML/JSON into a `Job` entity.
- `fetch_job(url: str, *, use_browser: bool, timeout_seconds: float) -> Job`: Dispatches fetch requests via standard HTTP (`httpx`) or delegates to Playwright if browser execution is requested.

### 2.2. Headless Browser Engine (`browser.py`)
- Configured as an **Optional Extra**: Dynamically imports `playwright.sync_api` at runtime.
- If uninstalled, emits an explicit diagnostic error instructing the user to install `mocnghe[browser]`.
- Launches Chromium with `headless=True` and waits for `networkidle` state to allow JavaScript single-page applications (SPAs) to finish client-side rendering.

### 2.3. Specialized Adapters
- **`GreenhouseAdapter`**: Extracts role title, company name, location, and `#content` description from standard Greenhouse layouts.
- **`ITviecAdapter`**: Detects Cloudflare/bot challenges and partitions the posting into structured sections (Description, Skills Required, Benefits).
- **`IndeedAdapter`**: Prioritizes `schema.org/JobPosting` JSON-LD structures and `window._initialData` state before falling back to DOM parsing.
- **`GenericAdapter`**: Fallback strategy for arbitrary career pages utilizing OpenGraph metadata and HTML5 semantic elements (`<main>`, `<article>`).

---

## 3. Deduplication & Content Hashing

1. Full posting details are compiled into a normalized `freeform_text`.
2. `hash_job_identity(freeform_text)` calculates a 64-character lowercase SHA-256 digest.
3. The canonical identifier `job_id` is assigned as `job_<first 16 hex chars>`.
4. In SQLite, the `jobs` table keys deduplication on `source_identity` (canonical URL or file path) when `dedupe_by_source_identity=True` is enabled, updating records rather than generating duplicates.
