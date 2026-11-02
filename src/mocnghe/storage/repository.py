import fcntl
import hashlib
import json
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import yaml
from pydantic import ValidationError

from ..models.job import Job
from ..models.profile import CandidateProfile


class CareerRepository:
    def __init__(self, workspace: str | Path) -> None:
        self.workspace: Path = self._safe_workspace(Path(workspace))
        self.profile_path: Path = self.workspace / "profile.json"
        self.drafts_dir: Path = self.workspace / "drafts"
        self.profiles_dir: Path = self.workspace / "profiles"
        self.reports_dir: Path = self.workspace / "reports"
        self.applications_dir: Path = self.workspace / "applications"
        self.pipeline_file: Path = self.workspace / "pipeline.md"
        self.jobs_dir: Path = self.workspace / "jobs"
        self.lock_file: Path = self.workspace / ".lock"

    def initialize(self) -> None:
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.drafts_dir.mkdir(parents=True, exist_ok=True)
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.applications_dir.mkdir(parents=True, exist_ok=True)
        self.jobs_dir.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def lock(self):
        self.initialize()
        with open(self.lock_file, "w") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

    def connect(self):
        """Deprecated compatibility alias for transaction lock."""
        return self.lock()

    def upsert_job(
        self,
        job: Job,
        source_identity: str,
        raw_content: str,
        *,
        dedupe_by_source_identity: bool = False,
    ) -> tuple[Job, bool]:
        if job.job_id is None or job.content_hash is None:
            raise ValueError("job_id and content_hash are required for persistence")
        self.initialize()
        with self.lock():
            existing_jobs = self.list_jobs()
            if dedupe_by_source_identity:
                for ej in existing_jobs:
                    if ej.job_id is None:
                        continue
                    obs = self.get_job_observations(ej.job_id)
                    if any(o.get("source_identity") == source_identity for o in obs) or ej.source.original_uri == source_identity:
                        self._insert_source_observation(ej, source_identity, raw_content)
                        return ej, False

            for ej in existing_jobs:
                if ej.content_hash == job.content_hash:
                    self._insert_source_observation(ej, source_identity, raw_content)
                    return ej, False

            self.save_job(job, raw_content)
            self._insert_source_observation(job, source_identity, raw_content)

            self.applications_dir.mkdir(parents=True, exist_ok=True)
            app_file = self.applications_dir / f"{job.job_id}.yaml"
            if not app_file.exists():
                app_data = {
                    "job_id": job.job_id,
                    "state": "discovered",
                    "cv_version": None,
                    "jd_content_hash": job.content_hash,
                    "applied_at": None,
                    "created_at": datetime.now(UTC).isoformat(),
                    "events": [],
                }
                app_file.write_text(yaml.safe_dump(app_data, allow_unicode=True, sort_keys=False), encoding="utf-8")

            return job, True

    def save_job(self, job: Job, raw_content: str | None = None) -> None:
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        job_md_file = self.jobs_dir / f"{job.job_id}.md"
        if raw_content is None:
            if job_md_file.exists():
                try:
                    parts = job_md_file.read_text(encoding="utf-8").split("---", 2)
                    raw_content = parts[2].strip() if len(parts) >= 3 else job.description
                except Exception:
                    raw_content = job.description
            else:
                raw_content = job.freeform_text or job.description
        job_md_file.write_text(self._render_job_markdown(job, raw_content), encoding="utf-8")

    def _render_job_markdown(self, job: Job, raw_content: str) -> str:
        frontmatter = {
            "job_id": job.job_id,
            "content_hash": job.content_hash,
            "title": job.title,
            "employer": job.employer,
            "location": job.location,
            "workplace_policy": job.workplace_policy,
            "employment_type": job.employment_type.value,
            "salary": job.salary.model_dump(mode="json"),
            "applied": job.applied,
            "source": {
                "source_id": job.source.source_id,
                "source_kind": job.source.source_kind,
                "original_uri": job.source.original_uri,
                "original_url": str(job.source.original_url) if job.source.original_url else None,
                "retrieved_at": job.source.retrieved_at.isoformat(),
            },
            "description": job.description,
            "requirements": job.requirements,
            "benefits": job.benefits,
            "freeform_text": job.freeform_text,
        }
        lines = [
            "---",
            yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False).strip(),
            "---",
            "",
            f"# {job.title} — {job.employer}",
            "",
            f"- **Location**: {job.location}",
            f"- **Workplace Policy**: {job.workplace_policy}",
            f"- **Employment Type**: {job.employment_type.value}",
            f"- **Salary**: {job.salary.currency or ''} {job.salary.minimum or ''} - {job.salary.maximum or ''}".strip(),
            "",
            "## Description",
            job.description or "*(No description)*",
            "",
            "## Requirements",
            job.requirements or "*(No requirements)*",
            "",
            "## Benefits",
            job.benefits or "*(No benefits)*",
            "",
        ]
        if job.freeform_text and job.freeform_text not in (job.description, job.requirements):
            lines.extend(["## Raw Freeform Text", job.freeform_text, ""])
        return "\n".join(lines)

    def _parse_job_markdown(self, path: Path) -> Job:
        content = path.read_text(encoding="utf-8")
        if not content.startswith("---"):
            raise ValueError(f"Not a frontmatter markdown file: {path}")
        parts = content.split("---", 2)
        if len(parts) < 3:
            raise ValueError(f"Malformed frontmatter in: {path}")
        fm = yaml.safe_load(parts[1])
        if not isinstance(fm, dict):
            raise TypeError(f"Invalid YAML frontmatter in: {path}")
        body = parts[2]

        from ..models.job import EmploymentType, Salary, SourceProvenance

        salary_data = fm.get("salary", {})
        source_data = fm.get("source", {})

        return Job(
            job_id=str(fm["job_id"]),
            content_hash=str(fm["content_hash"]),
            source=SourceProvenance.model_validate(source_data),
            title=str(fm["title"]),
            employer=str(fm["employer"]),
            location=str(fm["location"]),
            workplace_policy=str(fm.get("workplace_policy", "unknown")),
            employment_type=EmploymentType(str(fm.get("employment_type", "unknown"))),
            salary=Salary.model_validate(salary_data),
            description=str(fm.get("description", "")),
            requirements=str(fm.get("requirements", "")),
            benefits=str(fm.get("benefits", "")),
            freeform_text=str(fm.get("freeform_text", body.strip())),
            applied=bool(fm.get("applied", False)),
        )

    def list_jobs(self) -> list[Job]:
        if not self.jobs_dir.exists():
            return []
        jobs = []
        for md_file in sorted(self.jobs_dir.glob("*.md"), key=lambda p: p.stat().st_mtime):
            try:
                jobs.append(self._parse_job_markdown(md_file))
            except (yaml.YAMLError, ValidationError, OSError, ValueError):
                pass
        return jobs

    def get_job(self, job_id: str) -> Job | None:
        md_file = self.jobs_dir / f"{job_id}.md"
        if md_file.exists():
            return self._parse_job_markdown(md_file)
        return None

    def doctor(self) -> dict[str, str]:
        self.initialize()
        job_count = len(list(self.jobs_dir.glob("*.md"))) if self.jobs_dir.exists() else 0
        draft_count = len(list(self.drafts_dir.glob("*.yaml"))) if self.drafts_dir.exists() else 0
        profile_count = len(list(self.profiles_dir.glob("*.yaml"))) if self.profiles_dir.exists() else 0
        report_count = len(list(self.reports_dir.glob("*.yaml"))) if self.reports_dir.exists() else 0
        return {
            "database": "ok",
            "foreign_keys": "on",
            "jobs": str(job_count),
            "profile_drafts": str(draft_count),
            "profiles": str(profile_count),
            "evaluation_reports": str(report_count),
        }

    def get_profile_source_path(self) -> Path | None:
        for filename in ("profile.yaml", "profile.yml", "profile.json"):
            path = self.workspace / filename
            if path.exists():
                return path
        return None

    def profile_exists(self) -> bool:
        return self.get_profile_source_path() is not None

    def _render_profile_markdown(self, profile: CandidateProfile) -> str:
        lines = [
            "---",
            f"profile_id: {profile.profile_id}",
            f"version: {profile.version}",
            f"confirmed_at: {profile.confirmed_at.isoformat() if profile.confirmed_at else 'null'}",
            "---",
            "",
            f"# Candidate Profile: {profile.profile_id} ({profile.version})",
            "",
            "## Identity",
        ]
        if profile.identity:
            for k, v in profile.identity.items():
                lines.append(f"- **{k}**: {v}")
        else:
            lines.append("*(No identity details)*")
        lines.append("")

        lines.append("## Target Occupations")
        if profile.ranked_targets:
            for t in profile.ranked_targets:
                lines.append(f"- Rank {t.rank}: **{t.title}** ({t.occupation_family})")
        else:
            lines.append("*(No targets specified)*")
        lines.append("")

        lines.append("## Experience")
        if profile.experience:
            for exp in profile.experience:
                lines.append(f"- **{exp.title}** [{exp.engagement_type}] ({exp.start or '?'} to {exp.end or 'present'})")
        else:
            lines.append("*(No experience listed)*")
        lines.append("")

        lines.append("## Education")
        if profile.education:
            for edu in profile.education:
                lines.append(f"- {edu}")
        else:
            lines.append("*(No education listed)*")
        lines.append("")

        lines.append("## Skills & Languages")
        lines.append(f"- **Skills**: {', '.join(profile.skills) if profile.skills else 'None'}")
        lines.append(f"- **Languages**: {', '.join(profile.languages) if profile.languages else 'None'}")
        lines.append("")

        lines.append("## Evidence Grounding")
        for ev in profile.evidence:
            quote = f' - "{ev.source_quote}"' if ev.source_quote else ""
            lines.append(f"- `{ev.evidence_id}` [{ev.status.value if hasattr(ev.status, 'value') else ev.status}]: {ev.summary}{quote}")
        lines.append("")
        return "\n".join(lines)

    def save_profile_draft(self, draft_id: str, payload: dict[str, object]) -> None:
        self.initialize()
        self.drafts_dir.mkdir(parents=True, exist_ok=True)
        draft_file = self.drafts_dir / f"{draft_id}.yaml"
        draft_file.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=True), encoding="utf-8")

    def load_profile_draft(self, draft_id: str) -> dict[str, object] | None:
        self.initialize()
        draft_file = self.drafts_dir / f"{draft_id}.yaml"
        if draft_file.exists():
            data = yaml.safe_load(draft_file.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return cast(dict[str, object], data)
        return None

    def save_confirmed_profile(self, profile: CandidateProfile) -> None:
        self.initialize()
        if profile.confirmed_at is None:
            raise ValueError("confirmed profile requires confirmed_at")
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        yaml_file = self.profiles_dir / f"{profile.version}.yaml"
        if yaml_file.exists():
            raise ValueError("confirmed profile versions are immutable")

        payload_dict = profile.model_dump(mode="json")
        payload_dict["_hash"] = hashlib.sha256(profile.model_dump_json().encode()).hexdigest()
        yaml_file.write_text(yaml.safe_dump(payload_dict, allow_unicode=True, sort_keys=False), encoding="utf-8")

        md_file = self.profiles_dir / f"{profile.version}.md"
        md_file.write_text(self._render_profile_markdown(profile), encoding="utf-8")

    def get_profile_version(self, version: str) -> CandidateProfile | None:
        self.initialize()
        yaml_file = self.profiles_dir / f"{version}.yaml"
        if yaml_file.exists():
            data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.pop("_hash", None)
                return CandidateProfile.model_validate(data)
        return None

    def get_latest_profile(self) -> CandidateProfile | None:
        self.initialize()
        if self.profiles_dir.exists():
            yaml_files = sorted(self.profiles_dir.glob("*.yaml"), key=lambda p: p.stat().st_mtime, reverse=True)
            for f in yaml_files:
                try:
                    data = yaml.safe_load(f.read_text(encoding="utf-8"))
                    if isinstance(data, dict):
                        data.pop("_hash", None)
                        return CandidateProfile.model_validate(data)
                except (yaml.YAMLError, ValidationError, OSError):
                    pass
        return None

    def _render_evaluation_report_markdown(
        self,
        *,
        report_id: str,
        profile_version: str,
        job_id: str,
        jd_content_hash: str,
        runtime: str,
        model: str,
        data: dict[str, object],
    ) -> str:
        lines = [
            "---",
            f"report_id: {report_id}",
            f"profile_version: {profile_version}",
            f"job_id: {job_id}",
            f"jd_content_hash: {jd_content_hash}",
            f"runtime: {runtime}",
            f"model: {model}",
            "---",
            "",
            f"# Evaluation Report: {report_id}",
            "",
            f"- **Target Job ID**: {job_id}",
            f"- **Profile Version**: {profile_version}",
            f"- **Model**: {model} ({runtime})",
            "",
        ]
        if "recommendation" in data:
            lines.append(f"## Recommendation: {str(data['recommendation']).upper()}")
            lines.append("")
        if "fit_summary" in data:
            lines.append("## Fit Summary")
            lines.append(str(data["fit_summary"]))
            lines.append("")
        if "findings" in data and isinstance(data["findings"], list):
            lines.append("## Findings")
            for f in data["findings"]:
                lines.append(f"- {f}")
            lines.append("")
        return "\n".join(lines)

    def save_evaluation_report(
        self,
        *,
        report_id: str,
        profile_version: str,
        job_id: str,
        jd_content_hash: str,
        runtime: str,
        model: str,
        payload_json: str,
    ) -> None:
        self.initialize()
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        try:
            parsed = json.loads(payload_json)
            if isinstance(parsed, dict):
                data: dict[str, object] = {str(k): v for k, v in parsed.items()}
            else:
                data = {"raw_payload": parsed}
        except (json.JSONDecodeError, TypeError):
            data = {"raw_payload": payload_json}

        # Save YAML
        yaml_file = self.reports_dir / f"{report_id}.yaml"
        yaml_file.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")

        # Save Markdown
        md_file = self.reports_dir / f"{report_id}.md"
        md_file.write_text(
            self._render_evaluation_report_markdown(
                report_id=report_id,
                profile_version=profile_version,
                job_id=job_id,
                jd_content_hash=jd_content_hash,
                runtime=runtime,
                model=model,
                data=data,
            ),
            encoding="utf-8",
        )

    def count_evaluation_reports(self) -> int:
        self.initialize()
        return len(list(self.reports_dir.glob("*.yaml"))) if self.reports_dir.exists() else 0

    def _insert_source_observation(
        self,
        job: Job,
        source_identity: str,
        raw_content: str,
    ) -> None:
        if job.job_id is None or job.content_hash is None:
            raise ValueError("job_id and content_hash are required for source observations")
        obs_dir = self.workspace / "observations"
        obs_dir.mkdir(parents=True, exist_ok=True)
        obs_file = obs_dir / f"{job.job_id}.json"
        existing = []
        if obs_file.exists():
            try:
                existing = json.loads(obs_file.read_text(encoding="utf-8"))
            except Exception:
                existing = []
        item = {
            "job_id": job.job_id,
            "content_hash": job.content_hash,
            "source_id": job.source.source_id,
            "source_identity": source_identity,
            "source_kind": job.source.source_kind,
            "original_uri": job.source.original_uri,
            "original_url": str(job.source.original_url) if job.source.original_url else None,
            "retrieved_at": job.source.retrieved_at.isoformat(),
            "raw_content": raw_content,
        }
        for o in existing:
            if o.get("source_identity") == source_identity and o.get("raw_content") == raw_content:
                return
        existing.append(item)
        obs_file.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_job_observations(self, job_id: str) -> list[dict[str, object]]:
        obs_file = self.workspace / "observations" / f"{job_id}.json"
        if not obs_file.exists():
            return []
        try:
            data = json.loads(obs_file.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except Exception:
            pass
        return []

    def _safe_workspace(self, workspace: Path) -> Path:
        expanded = workspace.expanduser()
        if expanded.exists() and not expanded.is_dir():
            raise ValueError("workspace must be a directory")
        resolved_parent = expanded.parent.resolve()
        return resolved_parent / expanded.name
