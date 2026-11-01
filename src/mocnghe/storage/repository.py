import hashlib
import json
import sqlite3
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
        # Stable on-disk name: rebranding must reuse existing workspaces, not fork them.
        self.database_path: Path = self.workspace / "careerviet.sqlite3"
        self.profile_path: Path = self.workspace / "profile.json"
        self.drafts_dir: Path = self.workspace / "drafts"
        self.profiles_dir: Path = self.workspace / "profiles"
        self.reports_dir: Path = self.workspace / "reports"
        self.applications_dir: Path = self.workspace / "applications"
        self.pipeline_file: Path = self.workspace / "pipeline.md"
        self.jobs_dir: Path = self.workspace / "jobs"

    def initialize(self) -> None:
        self.workspace.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            # Serialize schema discovery and ALTERs, including concurrent first use.
            _ = connection.execute("BEGIN IMMEDIATE")
            _ = connection.execute(
                """
                create table if not exists jobs (
                    job_id text primary key,
                    content_hash text not null,
                    source_id text not null,
                    source_identity text not null,
                    source_kind text not null,
                    original_uri text not null,
                    original_url text,
                    retrieved_at text not null,
                    title text not null,
                    employer text not null,
                    location text not null,
                    workplace_policy text not null,
                    employment_type text not null,
                    salary_json text not null,
                    description text not null,
                    requirements text not null,
                    applied integer not null check (applied in (0, 1)),
                    raw_content text not null,
                    created_at text not null default current_timestamp,
                    unique (content_hash, source_identity)
                )
                """
            )
            self._ensure_jobs_columns(connection)
            _ = connection.execute(
                """
                create table if not exists applications (
                    application_id integer primary key,
                    job_id text not null references jobs(job_id) on delete cascade,
                    state text not null,
                    cv_version text,
                    jd_content_hash text,
                    applied_at text,
                    created_at text not null default current_timestamp
                )
                """
            )
            _ = connection.execute(
                """
                create table if not exists job_source_observations (
                    observation_id integer primary key,
                    job_id text not null references jobs(job_id) on delete cascade,
                    content_hash text not null,
                    source_id text not null,
                    source_identity text not null,
                    source_kind text not null,
                    original_uri text not null,
                    original_url text,
                    retrieved_at text not null,
                    raw_content text not null,
                    created_at text not null default current_timestamp,
                    unique (job_id, source_identity, retrieved_at, raw_content)
                )
                """
            )
            _ = connection.execute(
                """
                create table if not exists profile_drafts (
                    draft_id text primary key,
                    payload_json text not null,
                    updated_at text not null default current_timestamp
                )
                """
            )
            _ = connection.execute(
                """
                create table if not exists profiles (
                    profile_id text not null,
                    version text primary key,
                    payload_json text not null,
                    content_hash text not null,
                    confirmed_at text not null,
                    created_at text not null default current_timestamp
                )
                """
            )
            _ = connection.execute(
                """
                create table if not exists evaluation_reports (
                    report_id text primary key,
                    profile_version text not null,
                    job_id text not null,
                    jd_content_hash text not null,
                    runtime text not null,
                    model text not null,
                    payload_json text not null,
                    created_at text not null default current_timestamp
                )
                """
            )
            self._migrate_existing_source_observations(connection)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        _ = connection.execute("pragma foreign_keys = on")
        return connection

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
        with self.connect() as connection:
            if dedupe_by_source_identity:
                existing_by_source = cast(
                    sqlite3.Row | None,
                    connection.execute(
                        "select * from jobs where source_identity = ? order by created_at, job_id limit 1",
                        (source_identity,),
                    ).fetchone(),
                )
                if existing_by_source is not None:
                    existing_job = self._job_from_row(existing_by_source)
                    observed_job = job.model_copy(update={"job_id": existing_job.job_id})
                    self._insert_source_observation(connection, observed_job, source_identity, raw_content)
                    return existing_job, False
            existing = cast(
                sqlite3.Row | None,
                connection.execute(
                    "select * from jobs where content_hash = ? order by created_at, job_id limit 1",
                    (job.content_hash,),
                ).fetchone(),
            )
            if existing is not None:
                existing_job = self._job_from_row(existing)
                observed_job = job.model_copy(
                    update={"job_id": existing_job.job_id, "content_hash": existing_job.content_hash}
                )
                self._insert_source_observation(connection, observed_job, source_identity, raw_content)
                return existing_job, False
            _ = connection.execute(
                """
                insert into jobs (
                    job_id, content_hash, source_id, source_identity, source_kind, original_uri,
                    original_url, retrieved_at, title, employer, location, workplace_policy,
                    employment_type, salary_json, description, requirements, benefits, freeform_text,
                    applied, raw_content
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.job_id,
                    job.content_hash,
                    job.source.source_id,
                    source_identity,
                    job.source.source_kind,
                    job.source.original_uri,
                    str(job.source.original_url) if job.source.original_url else None,
                    job.source.retrieved_at.isoformat(),
                    job.title,
                    job.employer,
                    job.location,
                    job.workplace_policy,
                    job.employment_type.value,
                    job.salary.model_dump_json(),
                    job.description,
                    job.requirements,
                    job.benefits,
                    job.freeform_text,
                    1 if job.applied else 0,
                    raw_content,
                ),
            )
            self._insert_source_observation(connection, job, source_identity, raw_content)
            _ = connection.execute(
                "insert into applications (job_id, state, jd_content_hash) values (?, ?, ?)",
                (job.job_id, "discovered", job.content_hash),
            )
        self.applications_dir.mkdir(parents=True, exist_ok=True)
        app_file = self.applications_dir / f"{job.job_id}.yaml"
        app_data = {
            "job_id": job.job_id,
            "state": "discovered",
            "cv_version": None,
            "jd_content_hash": job.content_hash,
            "applied_at": None,
            "created_at": datetime.now(UTC).isoformat(),
            "events": [
                {
                    "from_state": "none",
                    "to_state": "discovered",
                    "recorded_at": datetime.now(UTC).isoformat(),
                }
            ],
        }
        app_file.write_text(yaml.safe_dump(app_data, allow_unicode=True, sort_keys=False), encoding="utf-8")

        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        job_md_file = self.jobs_dir / f"{job.job_id}.md"
        job_md_file.write_text(self._render_job_markdown(job, raw_content), encoding="utf-8")

        return job, True

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
            freeform_text=body.strip(),
            applied=bool(fm.get("applied", False)),
        )

    def list_jobs(self) -> list[Job]:
        with self.connect() as connection:
            rows = cast(
                list[sqlite3.Row],
                connection.execute("select * from jobs order by created_at, job_id").fetchall(),
            )
        if rows:
            return [self._job_from_row(row) for row in rows]
        if self.jobs_dir.exists():
            jobs = []
            for md_file in sorted(self.jobs_dir.glob("*.md")):
                try:
                    jobs.append(self._parse_job_markdown(md_file))
                except (yaml.YAMLError, ValidationError, OSError, ValueError):
                    pass
            return jobs
        return []

    def get_job(self, job_id: str) -> Job | None:
        with self.connect() as connection:
            row = cast(
                sqlite3.Row | None,
                connection.execute("select * from jobs where job_id = ?", (job_id,)).fetchone(),
            )
        if row is not None:
            return self._job_from_row(row)
        md_file = self.jobs_dir / f"{job_id}.md"
        if md_file.exists():
            return self._parse_job_markdown(md_file)
        return None

    def doctor(self) -> dict[str, str]:
        self.initialize()
        with self.connect() as connection:
            foreign_keys_row = cast(sqlite3.Row, connection.execute("pragma foreign_keys").fetchone())
            job_count_row = cast(sqlite3.Row, connection.execute("select count(*) from jobs").fetchone())
            draft_count_row = cast(sqlite3.Row, connection.execute("select count(*) from profile_drafts").fetchone())
            profile_count_row = cast(sqlite3.Row, connection.execute("select count(*) from profiles").fetchone())
            report_count_row = cast(sqlite3.Row, connection.execute("select count(*) from evaluation_reports").fetchone())
            foreign_keys = cast(int, foreign_keys_row[0])
            job_count = cast(int, job_count_row[0])
            draft_count = cast(int, draft_count_row[0])
            profile_count = cast(int, profile_count_row[0])
            report_count = cast(int, report_count_row[0])
        job_file_count = len(list(self.jobs_dir.glob("*.md"))) if self.jobs_dir.exists() else 0
        draft_file_count = len(list(self.drafts_dir.glob("*.yaml"))) if self.drafts_dir.exists() else 0
        profile_file_count = len(list(self.profiles_dir.glob("*.yaml"))) if self.profiles_dir.exists() else 0
        report_file_count = len(list(self.reports_dir.glob("*.yaml"))) if self.reports_dir.exists() else 0
        job_count = max(job_count, job_file_count)
        draft_count = max(draft_count, draft_file_count)
        profile_count = max(profile_count, profile_file_count)
        report_count = max(report_count, report_file_count)
        return {
            "database": "ok",
            "foreign_keys": "on" if foreign_keys == 1 else "off",
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
        payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        with self.connect() as connection:
            _ = connection.execute(
                """
                insert into profile_drafts (draft_id, payload_json, updated_at)
                values (?, ?, current_timestamp)
                on conflict(draft_id) do update set
                    payload_json = excluded.payload_json,
                    updated_at = current_timestamp
                """,
                (draft_id, payload_json),
            )

    def load_profile_draft(self, draft_id: str) -> dict[str, object] | None:
        self.initialize()
        draft_file = self.drafts_dir / f"{draft_id}.yaml"
        if draft_file.exists():
            data = yaml.safe_load(draft_file.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return cast(dict[str, object], data)
        with self.connect() as connection:
            row = cast(
                sqlite3.Row | None,
                connection.execute(
                    "select payload_json from profile_drafts where draft_id = ?", (draft_id,)
                ).fetchone(),
            )
        if row is None:
            return None
        return cast(dict[str, object], json.loads(cast(str, row["payload_json"])))

    def save_confirmed_profile(self, profile: CandidateProfile) -> None:
        self.initialize()
        if profile.confirmed_at is None:
            raise ValueError("confirmed profile requires confirmed_at")
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        yaml_file = self.profiles_dir / f"{profile.version}.yaml"
        if yaml_file.exists():
            raise ValueError("confirmed profile versions are immutable")

        with self.connect() as connection:
            existing = connection.execute(
                "select version from profiles where version = ?", (profile.version,)
            ).fetchone()
            if existing is not None:
                raise ValueError("confirmed profile versions are immutable")

        payload_dict = profile.model_dump(mode="json")
        yaml_file.write_text(yaml.safe_dump(payload_dict, allow_unicode=True, sort_keys=False), encoding="utf-8")

        md_file = self.profiles_dir / f"{profile.version}.md"
        md_file.write_text(self._render_profile_markdown(profile), encoding="utf-8")

        payload_json = profile.model_dump_json()
        content_hash = hashlib.sha256(payload_json.encode()).hexdigest()
        with self.connect() as connection:
            _ = connection.execute(
                """
                insert into profiles (profile_id, version, payload_json, content_hash, confirmed_at)
                values (?, ?, ?, ?, ?)
                """,
                (
                    profile.profile_id,
                    profile.version,
                    payload_json,
                    content_hash,
                    profile.confirmed_at.isoformat(),
                ),
            )

    def get_profile_version(self, version: str) -> CandidateProfile | None:
        self.initialize()
        with self.connect() as connection:
            row = cast(
                sqlite3.Row | None,
                connection.execute("select payload_json from profiles where version = ?", (version,)).fetchone(),
            )
        if row is not None:
            return CandidateProfile.model_validate_json(cast(str, row["payload_json"]))
        yaml_file = self.profiles_dir / f"{version}.yaml"
        if yaml_file.exists():
            data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return CandidateProfile.model_validate(data)
        return None

    def get_latest_profile(self) -> CandidateProfile | None:
        self.initialize()
        with self.connect() as connection:
            row = cast(
                sqlite3.Row | None,
                connection.execute(
                    "select payload_json from profiles order by created_at desc, version desc limit 1"
                ).fetchone(),
            )
        if row is not None:
            return CandidateProfile.model_validate_json(cast(str, row["payload_json"]))
        if self.profiles_dir.exists():
            yaml_files = sorted(self.profiles_dir.glob("*.yaml"), key=lambda p: p.stat().st_mtime, reverse=True)
            for f in yaml_files:
                try:
                    data = yaml.safe_load(f.read_text(encoding="utf-8"))
                    if isinstance(data, dict):
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

        with self.connect() as connection:
            _ = connection.execute(
                """
                insert into evaluation_reports (
                    report_id, profile_version, job_id, jd_content_hash, runtime, model, payload_json
                ) values (?, ?, ?, ?, ?, ?, ?)
                """,
                (report_id, profile_version, job_id, jd_content_hash, runtime, model, payload_json),
            )

    def count_evaluation_reports(self) -> int:
        self.initialize()
        file_count = len(list(self.reports_dir.glob("*.yaml"))) if self.reports_dir.exists() else 0
        with self.connect() as connection:
            row = cast(
                sqlite3.Row,
                connection.execute("select count(*) from evaluation_reports").fetchone(),
            )
        db_count = cast(int, row[0])
        return max(db_count, file_count)

    def _job_from_row(self, row: sqlite3.Row) -> Job:
        from ..models.job import EmploymentType, Salary, SourceProvenance

        salary_data = cast(object, json.loads(cast(str, row["salary_json"])))
        original_url = cast(str | None, row["original_url"])
        retrieved_at = datetime.fromisoformat(cast(str, row["retrieved_at"]))
        return Job(
            job_id=cast(str, row["job_id"]),
            content_hash=cast(str, row["content_hash"]),
            source=SourceProvenance.model_validate(
                {
                    "source_id": cast(str, row["source_id"]),
                    "source_kind": cast(str, row["source_kind"]),
                    "original_uri": cast(str, row["original_uri"]),
                    "original_url": original_url,
                    "retrieved_at": retrieved_at,
                }
            ),
            title=cast(str, row["title"]),
            employer=cast(str, row["employer"]),
            location=cast(str, row["location"]),
            workplace_policy=cast(str, row["workplace_policy"]),
            employment_type=EmploymentType(cast(str, row["employment_type"])),
            salary=Salary.model_validate(salary_data),
            description=cast(str, row["description"]),
            requirements=cast(str, row["requirements"]),
            benefits=cast(str, row["benefits"]),
            freeform_text=cast(str, row["freeform_text"]),
            applied=bool(cast(int, row["applied"])),
        )

    def _ensure_jobs_columns(self, connection: sqlite3.Connection) -> None:
        rows = cast(list[sqlite3.Row], connection.execute("pragma table_info(jobs)").fetchall())
        columns = {cast(str, row["name"]) for row in rows}
        if "benefits" not in columns:
            _ = connection.execute("alter table jobs add column benefits text not null default ''")
        if "freeform_text" not in columns:
            _ = connection.execute("alter table jobs add column freeform_text text not null default ''")

    def _migrate_existing_source_observations(self, connection: sqlite3.Connection) -> None:
        _ = connection.execute(
            """
            insert or ignore into job_source_observations (
                job_id, content_hash, source_id, source_identity, source_kind, original_uri,
                original_url, retrieved_at, raw_content
            )
            select
                job_id, content_hash, source_id, source_identity, source_kind, original_uri,
                original_url, retrieved_at, raw_content
            from jobs
            """
        )

    def _insert_source_observation(
        self,
        connection: sqlite3.Connection,
        job: Job,
        source_identity: str,
        raw_content: str,
    ) -> None:
        if job.job_id is None or job.content_hash is None:
            raise ValueError("job_id and content_hash are required for source observations")
        _ = connection.execute(
            """
            insert or ignore into job_source_observations (
                job_id, content_hash, source_id, source_identity, source_kind, original_uri,
                original_url, retrieved_at, raw_content
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job.job_id,
                job.content_hash,
                job.source.source_id,
                source_identity,
                job.source.source_kind,
                job.source.original_uri,
                str(job.source.original_url) if job.source.original_url else None,
                job.source.retrieved_at.isoformat(),
                raw_content,
            ),
        )

    def _safe_workspace(self, workspace: Path) -> Path:
        expanded = workspace.expanduser()
        if expanded.exists() and not expanded.is_dir():
            raise ValueError("workspace must be a directory")
        resolved_parent = expanded.parent.resolve()
        return resolved_parent / expanded.name
