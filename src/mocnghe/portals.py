import re
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError

from .models.job import Job


class TitleFilter(BaseModel):
    positive: list[str] = Field(default_factory=list)
    negative: list[str] = Field(default_factory=list)


class LocationFilter(BaseModel):
    allow: list[str] = Field(default_factory=list)
    negative: list[str] = Field(default_factory=list)


class ContentFilter(BaseModel):
    negative: list[str] = Field(default_factory=list)


class PortalSource(BaseModel):
    name: str
    urls: list[str] = Field(default_factory=list)
    enabled: bool = True


class PortalConfig(BaseModel):
    title_filter: TitleFilter = Field(default_factory=TitleFilter)
    location_filter: LocationFilter = Field(default_factory=LocationFilter)
    content_filter: ContentFilter = Field(default_factory=ContentFilter)
    sources: list[PortalSource] = Field(default_factory=list)


def _contains_term(text: str, term: str) -> bool:
    norm_text = text.lower()
    norm_term = term.lower().strip()
    if not norm_term:
        return False
    # Use word boundary or loose substring if term contains non-alphanumeric
    if re.search(r"^\w+$", norm_term):
        return bool(re.search(rf"\b{re.escape(norm_term)}\b", norm_text))
    return norm_term in norm_text


def validate_portals_config(path: Path) -> list[str]:
    if not path.exists():
        return [f"File does not exist: {path}"]
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return ["Invalid YAML structure: root must be a mapping."]
        PortalConfig.model_validate(data)
        return []
    except (yaml.YAMLError, ValidationError, OSError) as error:
        return [str(error)]


def load_portals_config(workspace: Path) -> PortalConfig | None:
    for filename in ("portals.yaml", "portals.yml"):
        file_path = workspace / filename
        if file_path.exists():
            try:
                data = yaml.safe_load(file_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return PortalConfig.model_validate(data)
            except (yaml.YAMLError, ValidationError, OSError):
                return None
    return None


def filter_job(config: PortalConfig, job: Job) -> tuple[bool, str | None]:
    # 1. Negative title filter
    for neg in config.title_filter.negative:
        if _contains_term(job.title, neg):
            return False, f"Excluded by negative title filter: '{neg}'"

    # 2. Positive title filter
    if config.title_filter.positive:
        matched_pos = any(_contains_term(job.title, pos) for pos in config.title_filter.positive)
        if not matched_pos:
            return False, "Job title does not match any positive title filters."

    # 3. Negative location filter
    for neg_loc in config.location_filter.negative:
        if _contains_term(job.location, neg_loc):
            return False, f"Excluded by negative location filter: '{neg_loc}'"

    # 4. Allowed location filter
    if config.location_filter.allow and job.location.lower() != "unknown":
        allowed = any(_contains_term(job.location, al_loc) for al_loc in config.location_filter.allow)
        if not allowed:
            return False, f"Location '{job.location}' not in allowed locations: {config.location_filter.allow}"

    # 5. Negative content filter
    corpus = f"{job.title} {job.employer} {job.description} {job.requirements} {job.freeform_text}"
    for neg_content in config.content_filter.negative:
        if _contains_term(corpus, neg_content):
            return False, f"Excluded by negative content filter keyword: '{neg_content}'"

    return True, None
