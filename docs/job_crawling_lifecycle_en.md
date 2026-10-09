# Job Ingestion Lifecycle: From Job URL to Local Storage

This document details the exact sequence of internal operations executed when a user or AI Agent provides a job posting URL: how adapters are resolved, how dynamic JavaScript pages are rendered, how data is parsed, and how duplicates are prevented in local storage.

---

## 1. High-Level Pipeline Architecture

```
[ User / AI Agent Provides Job URL ]
  (Greenhouse, ITviec, Indeed, or any career page)
            |
            v
[ STEP 1: Adapter Resolution (Registry Dispatch) ]
   - Extracts hostname from URL via urlparse
   - Scans registered adapters in priority order:
       1. GreenhouseAdapter (*.greenhouse.io)
       2. ITviecAdapter (itviec.com)
       3. IndeedAdapter (*.indeed.com)
       4. GenericAdapter (Fallback for all other domains)
            |
            v
[ STEP 2: Fetching & Dynamic Page Handling (Fetch Engine) ]
   - Static HTTP Mode (Default):
       * httpx.Client issues GET with modern desktop User-Agent
       * Automatically resolves redirects and checks status codes
   - Headless Browser Mode (--browser):
       * Launches Chromium via Playwright
       * Awaits `networkidle` event to ensure AJAX/SPA payloads finish
       * Captures fully hydrated client-side DOM
            |
            v
[ STEP 3: Domain-Specific Parsing & Normalization ]
   - Site-specific extraction strategies:
       * Greenhouse: h1.app-title, span.company-name, #content block
       * ITviec: Bot challenge detection, section partitioning (Description/Skills/Benefits)
       * Indeed: Prioritizes JSON-LD JobPosting schema, window._initialData, fallback DOM
       * Generic: OpenGraph metadata (og:title, og:site_name), semantic tags (<main>, <article>)
   - Aggregates canonical normalized text: `freeform_text`
            |
            v
[ STEP 4: Cryptographic Identity Fingerprinting ]
   - Normalizes whitespace via `normalize_job_content()`
   - Computes SHA-256 fingerprint: `content_hash = hash_job_identity(freeform_text)`
   - Derives canonical ID: `job_id = job_<first 16 hex chars>`
            |
            v
[ STEP 5: Persistence & Deduplication ]
   - Calls `CareerRepository.upsert_job(dedupe_by_source_identity=True)`
   - Keys unique constraints on the source URL (`source_identity`)
   - Existing JD: Updates content while preserving existing application state
   - New JD: Creates record, setting `applied = False`
```

---

## 2. Step-by-Step Breakdown

### Step 1: Adapter Resolution (`find_adapter`)
- **Operation:** When a URL is supplied (e.g. `https://itviec.com/it-jobs/senior-python-dev`), `find_adapter(url)` iterates through `_ADAPTERS` registered in `registry.py`.
- **Mechanism:** Checks domain compatibility via `adapter.supports_url(url)`. If no specialized handler matches, `GenericAdapter` is chosen as a safe fallback.

### Step 2: Fetching & Dynamic Page Handling
- **Static HTTP (`httpx`):** Selected by default for maximum speed (sub-second execution).
- **Headless Browser (`Playwright`):** Triggered when `--browser` is passed or for single-page applications:
  - Spawns background Chromium process.
  - Injects realistic desktop User-Agent headers.
  - Waits until background network traffic subsides (`wait_until="networkidle"`).
  - Retrieves fully rendered post-hydration HTML.

### Step 3: Domain-Specific Parsing & Normalization
Adapters apply targeted strategies to acquire clean content:
- **Indeed:** Prioritizes `application/ld+json` blocks. This schema holds raw posting data sent directly to search engines, completely immune to frontend layout changes.
- **ITviec:** Proactively checks for anti-bot indicators (`cf-challenge`, `hcaptcha`). If detected, raises an explicit error rather than storing challenge markup.
- **`freeform_text` Compilation:** Concatenates title, company, location, URL, and body into a cohesive document for downstream requirement extraction.

### Step 4: Cryptographic Fingerprinting
- Avoids random IDs. Every JD is deterministic and content-anchored.
- `hash_job_identity(freeform_text)` generates a 64-character lowercase hex digest.
- `job_id` is assigned as `job_<first 16 chars>`.

### Step 5: Local Persistence & Deduplication
- Records are committed to SQLite (`careerviet.sqlite3`).
- The `source_identity` column guarantees that re-crawling the same job URL updates existing entries (`existing`) rather than polluting the workspace with duplicates.
