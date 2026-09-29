from __future__ import annotations

import json
import re
from datetime import UTC, datetime

from bs4 import BeautifulSoup

from ...models.job import Job, SourceProvenance, hash_job_identity, job_id_from_hash
from .base import BaseJobAdapter


class IndeedAdapter(BaseJobAdapter):
    """Adapter for Indeed job postings (*.indeed.com)."""

    name = "indeed"
    domains = ("indeed.com",)

    def parse_job(self, content: str, *, url: str) -> Job:
        soup = BeautifulSoup(content, "html.parser")

        # 1. Try structured data JSON-LD first (common on Indeed)
        for script in soup.find_all("script", type="application/ld+json"):
            if not script.string:
                continue
            try:
                data = json.loads(script.string)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict) and data.get("@type") == "JobPosting":
                return self._job_from_jsonld(data, url=url)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and item.get("@type") == "JobPosting":
                        return self._job_from_jsonld(item, url=url)

        # 2. Try _initialData embedded state script
        state_match = re.search(r"window\._initialData\s*=\s*({.*?});</script>", content, re.DOTALL)
        if state_match:
            try:
                initial_data = json.loads(state_match.group(1))
            except json.JSONDecodeError:
                initial_data = {}
            job_data = initial_data.get("jobInfoWrapperModel", {}).get("jobInfoModel", {})
            if isinstance(job_data, dict) and job_data:
                return self._job_from_initial_data(job_data, url=url)

        # 3. DOM HTML fallback
        title_el = (
            soup.find("h1", class_=lambda c: c and "jobsearch-JobInfoHeader-title" in c)
            or soup.find("h1")
        )
        title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            og_title = soup.find("meta", property="og:title")
            if og_title and og_title.get("content"):
                title = str(og_title["content"]).split(" - ")[0].strip()
        if not title:
            title = "Untitled Indeed Role"

        employer_el = (
            soup.select_one("[data-company-name='true'], [data-testid='inlineHeader-companyName']")
            or soup.select_one(".jobsearch-InlineCompanyRating-companyHeader, .companyName")
        )
        employer = employer_el.get_text(strip=True) if employer_el else ""
        if not employer:
            og_desc = soup.find("meta", property="og:description")
            if og_desc and og_desc.get("content"):
                # "Company - Location - Description" pattern
                parts = str(og_desc["content"]).split(" - ")
                if len(parts) >= 2:
                    employer = parts[0].strip()
        if not employer:
            employer = "Indeed Employer"

        loc_el = (
            soup.select_one("[data-testid='inlineHeader-companyLocation'], [data-testid='job-location']")
            or soup.select_one(".jobsearch-JobInfoHeader-companyLocation, .companyLocation")
        )
        location = loc_el.get_text(strip=True) if loc_el else "unknown"

        body_el = (
            soup.find("div", id="jobDescriptionText")
            or soup.find("div", class_=lambda c: c and "jobDescriptionText" in c)
            or soup.find("main")
            or soup.body
        )
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
                "source_id": f"indeed:{url}",
                "source_kind": "indeed",
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

    def _job_from_jsonld(self, data: dict[str, object], *, url: str) -> Job:
        title = str(data.get("title") or "Untitled Indeed Role")

        hiring_org = data.get("hiringOrganization")
        if isinstance(hiring_org, dict):
            employer = str(hiring_org.get("name") or "Indeed Employer")
        else:
            employer = "Indeed Employer"

        job_loc = data.get("jobLocation")
        location = "unknown"
        if isinstance(job_loc, dict):
            addr = job_loc.get("address")
            if isinstance(addr, dict):
                parts = [
                    str(addr.get(k))
                    for k in ("addressLocality", "addressRegion", "addressCountry")
                    if addr.get(k)
                ]
                location = ", ".join(parts) or "unknown"

        desc = str(data.get("description") or "")
        desc_soup = BeautifulSoup(desc, "html.parser")
        body_text = desc_soup.get_text(separator="\n", strip=True)

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
                "source_id": f"indeed:{url}",
                "source_kind": "indeed",
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

    def _job_from_initial_data(self, job_data: dict[str, object], *, url: str) -> Job:
        header = job_data.get("jobInfoHeaderModel", {})
        title = "Untitled Indeed Role"
        employer = "Indeed Employer"
        location = "unknown"

        if isinstance(header, dict):
            title = str(header.get("jobTitle") or title)
            employer = str(header.get("companyName") or employer)
            location = str(header.get("formattedLocation") or location)

        desc_raw = str(job_data.get("sanitizedJobDescription") or "")
        desc_soup = BeautifulSoup(desc_raw, "html.parser")
        body_text = desc_soup.get_text(separator="\n", strip=True)

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
                "source_id": f"indeed:{url}",
                "source_kind": "indeed",
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
