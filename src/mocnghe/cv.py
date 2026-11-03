"""Local, immutable CV revisions. Citations validate quotes, not rewritten semantics."""
import hashlib
import json
from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models.job import Job
from .storage.repository import CareerRepository


def digest(value: BaseModel) -> str:
    # Workflow metadata is not JD content.
    if isinstance(value, Job):
        value = value.model_copy(update={"applied": False})
    return hashlib.sha256(json.dumps(value.model_dump(mode="json"), sort_keys=True,
                                     ensure_ascii=False).encode()).hexdigest()


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_id: str
    source_quote: str = Field(min_length=1, max_length=12000)
    text: str = Field(min_length=1, max_length=12000)
    section: Literal["experience", "education", "skills", "credentials", "other"] = "other"
    mode: Literal["extractive", "proposed"] = "extractive"
    uncertainty: str
    status: str

    @field_validator("section", mode="before")
    @classmethod
    def _normalize_section(cls, v: object) -> object:
        if isinstance(v, str):
            aliases = {
                "summary": "other",
                "objective": "other",
                "profile": "other",
                "projects": "other",
                "project": "other",
                "certifications": "credentials",
                "certification": "credentials",
                "certificate": "credentials",
                "certificates": "credentials",
                "licenses": "credentials",
                "license": "credentials",
                "work_experience": "experience",
                "work": "experience",
                "employment": "experience",
                "academic": "education",
                "degrees": "education",
                "skill": "skills",
                "technical_skills": "skills",
            }
            clean = v.strip().lower()
            return aliases.get(clean, clean)
        return v

    @field_validator("mode", mode="before")
    @classmethod
    def _normalize_mode(cls, v: object) -> object:
        if isinstance(v, str):
            clean = v.strip().lower()
            if clean in {"rewrite", "rewritten", "tailored", "translated"}:
                return "proposed"
            return clean
        return v


class CV(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    profile_version: str
    profile_hash: str
    job_id: str | None = None
    job_hash: str | None = None
    language: Literal["en", "vi"]
    identity: dict[str, str] = Field(default_factory=dict)
    claims: list[Claim] = Field(min_length=1, max_length=100)
    provenance: str = "local-extractive"
    warning: str = "Original evidence language retained; translations/rewrites need human review."


class CVService:
    def __init__(self, repository: CareerRepository):
        self.repo = repository
        self.cvs_dir = repository.workspace / "cvs"
        repository.initialize()

    content_hash = staticmethod(digest)

    def _render_cv_markdown(self, cv: CV) -> str:
        display_name = cv.identity.get("name") or cv.identity.get("full_name") or "Curriculum Vitae"
        lines = [
            "---",
            f"id: {cv.id}",
            f"profile_version: {cv.profile_version}",
            f"language: {cv.language}",
            f"job_id: {cv.job_id or 'null'}",
            f"provenance: {cv.provenance}",
            "---",
            "",
            f"# {display_name}",
            "",
        ]
        if cv.identity:
            lines.append("## Contact Information")
            for k, v in cv.identity.items():
                lines.append(f"- **{k.title()}**: {v}")
            lines.append("")

        sections = ["experience", "education", "skills", "credentials", "other"]
        for sec in sections:
            sec_claims = [c for c in cv.claims if c.section == sec]
            if sec_claims:
                lines.append(f"## {sec.title()}")
                for c in sec_claims:
                    quote = f' (quote: "{c.source_quote}")' if c.source_quote != c.text else ""
                    lines.append(f"- {c.text}{quote} <!-- [{c.evidence_id}: {c.status}] -->")
                lines.append("")
        return "\n".join(lines)

    def _profile(self, version):
        profile = self.repo.get_profile_version(version)
        if profile is not None:
            yaml_file = self.repo.profiles_dir / f"{version}.yaml"
            actual = hashlib.sha256(profile.model_dump_json().encode()).hexdigest()
            if yaml_file.exists():
                stored_data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
                stored_hash = stored_data.get("_hash")
                if stored_hash is not None and stored_hash != actual:
                    raise ValueError("stale canonical profile: stored integrity hash mismatch")
        return profile

    def create(self, version, evidence_ids, *, language, job_id=None, identity_keys=()):
        profile = self._profile(version)
        if profile is None or profile.confirmed_at is None:
            raise ValueError("confirmed profile required")
        evidence = {e.evidence_id: e for e in profile.evidence}
        if not evidence_ids or len(set(evidence_ids)) != len(evidence_ids):
            raise ValueError("select unique evidence ids")
        if any(i not in evidence for i in evidence_ids):
            raise ValueError("unknown evidence id")
        if any(k not in profile.identity for k in identity_keys):
            raise ValueError("unknown identity key")
        job = self.repo.get_job(job_id) if job_id else None
        if job_id and job is None:
            raise ValueError("job not found")
        claims = []
        for key in evidence_ids:
            e = evidence[key]
            if e.provenance == "identity" or key.startswith("ev_identity"):
                raise ValueError("identity evidence must not be used as a CV claim")
            quote = e.source_quote or e.summary
            prov = (e.provenance or "").lower()
            if prov in {"experience", "cv_experience", "work_experience"}:
                section = "experience"
            elif prov in {"education", "cv_education"}:
                section = "education"
            elif prov in {"skills", "cv_skills", "skill", "technical_skills"}:
                section = "skills"
            elif prov in {"credentials", "cv_certifications", "certifications", "licenses"}:
                section = "credentials"
            elif key.startswith("ev_exp_"):
                section = "experience"
            elif key.startswith("ev_edu_"):
                section = "education"
            elif key.startswith("ev_skills_"):
                section = "skills"
            elif key.startswith("ev_cert_"):
                section = "credentials"
            else:
                section = "other"
            claims.append(Claim(evidence_id=key, source_quote=quote, text=quote,
                                section=section, uncertainty=e.uncertainty, status=e.status.value))
        cv = CV(id=uuid4().hex, profile_version=version, profile_hash=digest(profile),
                job_id=job_id, job_hash=digest(job) if job else None,
                language=language, claims=claims,
                identity={k: profile.identity[k] for k in identity_keys})
        self._save(cv)
        return cv

    def validate(self, cv):
        profile = self._profile(cv.profile_version)
        if profile is None or profile.confirmed_at is None or digest(profile) != cv.profile_hash:
            raise ValueError("stale canonical profile")
        job = self.repo.get_job(cv.job_id) if cv.job_id else None
        if (digest(job) if job else None) != cv.job_hash or (cv.job_id and job is None):
            raise ValueError("stale canonical job")
        evidence = {e.evidence_id: e for e in profile.evidence}
        ids = [c.evidence_id for c in cv.claims]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate evidence ids")
        for c in cv.claims:
            e = evidence.get(c.evidence_id)
            if e is None or e.provenance == "identity" or c.evidence_id.startswith("ev_identity"):
                raise ValueError("unknown or private evidence")
            if c.source_quote != (e.source_quote or e.summary):
                raise ValueError("noncanonical quote")
            if c.uncertainty != e.uncertainty or c.status != e.status.value:
                raise ValueError("noncanonical evidence status")
            if c.mode == "extractive" and c.text != c.source_quote:
                raise ValueError("extractive text must equal canonical quote")
        if any(profile.identity.get(k) != v for k, v in cv.identity.items()):
            raise ValueError("noncanonical identity")

    def _save(self, cv):
        self.validate(cv)
        self.cvs_dir.mkdir(parents=True, exist_ok=True)
        yaml_path = self.cvs_dir / f"{cv.id}.yaml"
        payload_data = cv.model_dump(mode="json")
        payload_data["_hash"] = digest(cv)
        yaml_path.write_text(yaml.safe_dump(payload_data, allow_unicode=True, sort_keys=False), encoding="utf-8")
        md_path = self.cvs_dir / f"{cv.id}.md"
        md_path.write_text(self._render_cv_markdown(cv), encoding="utf-8")

    def get(self, cv_id):
        yaml_path = self.cvs_dir / f"{cv_id}.yaml"
        if not yaml_path.exists():
            raise ValueError("CV not found")
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        stored_hash = data.pop("_hash", None)
        cv = CV.model_validate(data)
        if cv.id != cv_id or (stored_hash is not None and digest(cv) != stored_hash):
            raise ValueError("CV content hash mismatch")
        self.validate(cv)
        return cv

    def revise(self, cv_id, claims, *, provenance):
        old = self.get(cv_id)
        payload = old.model_dump()
        payload.update(id=uuid4().hex, claims=claims, provenance=provenance)
        cv = CV.model_validate(payload)
        self._save(cv)
        return cv

    def approve(self, cv_id, content_hash):
        cv = self.get(cv_id)
        if digest(cv) != content_hash:
            raise ValueError("approval hash does not match reviewed content")
        self.cvs_dir.mkdir(parents=True, exist_ok=True)
        appr_path = self.cvs_dir / f"{cv_id}.approval.yaml"
        appr_data = {
            "cv_id": cv_id,
            "content_hash": content_hash,
            "approved_at": datetime.now(UTC).isoformat(),
        }
        appr_path.write_text(yaml.safe_dump(appr_data, allow_unicode=True), encoding="utf-8")

    def approved(self, cv_id):
        cv = self.get(cv_id)
        appr_path = self.cvs_dir / f"{cv_id}.approval.yaml"
        if appr_path.exists():
            data = yaml.safe_load(appr_path.read_text(encoding="utf-8"))
            return isinstance(data, dict) and data.get("content_hash") == digest(cv)
        return False
