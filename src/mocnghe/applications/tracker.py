"""Transactional local state transitions and append-only event history."""
import hashlib
import json
from datetime import UTC, datetime
from typing import Any

import yaml

from ..cv import CVService, digest
from ..models.application import ApplicationState
from ..models.profile import CandidateProfile

TRANSITIONS = {
    "discovered": {"shortlisted", "archived"},
    "shortlisted": {"drafting", "withdrawn", "archived"},
    "drafting": {"ready", "shortlisted", "withdrawn", "archived"},
    "ready": {"drafting", "applied", "withdrawn", "archived"},
    "applied": {"interviewing", "offer", "rejected", "withdrawn", "archived"},
    "interviewing": {"offer", "rejected", "withdrawn", "archived"},
    "offer": {"withdrawn", "archived"},
    "rejected": {"archived"}, "withdrawn": {"archived"}, "archived": set(),
}


class ApplicationTracker:
    def __init__(self, repo):
        self.repo = repo
        self.applications_dir = repo.workspace / "applications"
        self.pipeline_file = repo.workspace / "pipeline.md"
        repo.initialize()

    def _app_file(self, job_id):
        return self.applications_dir / f"{job_id}.yaml"

    def _load(self, job_id):
        f = self._app_file(job_id)
        if not f.exists():
            raise ValueError("application not found")
        data = yaml.safe_load(f.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("application not found")
        if data.get("submission_json") is not None:
            actual = hashlib.sha256(data["submission_json"].encode()).hexdigest()
            if actual != data.get("submission_hash"):
                raise ValueError("submission snapshot hash mismatch")
        return data

    def get(self, job_id):
        return self._load(job_id)

    def list(self, state=None):
        if state is not None:
            ApplicationState(state)
        if not self.applications_dir.exists():
            return []
        apps = []
        for f in sorted(self.applications_dir.glob("*.yaml")):
            try:
                row = self._load(f.stem)
                if state is None or row.get("state") == state:
                    apps.append(row)
            except ValueError:
                pass
        return apps

    def history(self, job_id):
        row = self._load(job_id)
        events = row.get("events", [])
        return [
            {
                "event_id": idx + 1,
                "job_id": job_id,
                "from_state": ev.get("from_state", "none"),
                "to_state": ev.get("to_state", "none"),
                "recorded_at": ev.get("recorded_at", ""),
            }
            for idx, ev in enumerate(events)
        ]

    def transition(self, job_id, state, *, cv_id=None, confirm=False):
        if state == "applied" and confirm is not True:
            raise PermissionError("explicit confirmation of manual submission required")
        if state not in {"ready", "applied"} and cv_id is not None:
            raise ValueError("CV selection only allowed for ready/applied")
        snapshot = None
        cv = None
        job = None
        if state in {"ready", "applied"}:
            if not cv_id:
                raise ValueError("approved CV required")
            cvs = CVService(self.repo)
            cv = cvs.get(cv_id)
            if not cvs.approved(cv_id):
                raise PermissionError("approved CV required")
            job = self.repo.get_job(job_id)
            if job is None or (cv.job_id and cv.job_id != job_id):
                raise ValueError("CV targets a different or missing job")
            profile = self.repo.get_profile_version(cv.profile_version)
            if profile is None:
                raise ValueError("profile not found")
            snapshot = json.dumps({"cv": cv.model_dump(mode="json"), "cv_hash": digest(cv),
                                   "job": job.model_dump(mode="json"), "job_hash": digest(job),
                                   "profile_version": cv.profile_version}, sort_keys=True)

        with self.repo.lock():
            row = self._load(job_id)
            if state not in TRANSITIONS.get(row["state"], set()):
                raise ValueError("invalid application transition")
            if snapshot is not None and cv is not None and job is not None:
                current_job = self.repo.get_job(job_id)
                current_profile = self.repo.get_profile_version(cv.profile_version)
                if (current_job is None or current_profile is None or
                        current_profile.confirmed_at is None or
                        digest(current_profile) != cv.profile_hash or
                        (cv.job_id is not None and digest(current_job) != cv.job_hash)):
                    raise ValueError("stale canonical profile or targeted job")
                cvs = CVService(self.repo)
                stored_cv = cvs.get(cv_id)
                if (digest(current_job) != digest(job) or
                        stored_cv is None or digest(stored_cv) != digest(cv) or
                        not cvs.approved(cv_id)):
                    raise ValueError("canonical content changed during transition")
                if state == "applied" and (row.get("cv_version") != cv_id or row.get("submission_json") != snapshot):
                    raise ValueError("ready selection is stale; return to drafting and review")
                row["cv_version"] = cv_id
                row["jd_content_hash"] = job.content_hash
                row["submission_json"] = snapshot
                row["submission_hash"] = hashlib.sha256(snapshot.encode()).hexdigest()

            if state == "applied":
                row["applied_at"] = datetime.now(UTC).isoformat()
                job_obj = self.repo.get_job(job_id)
                if job_obj:
                    job_obj.applied = True
                    self.repo.save_job(job_obj)

            prev_state = row["state"]
            row["state"] = state
            if "events" not in row:
                row["events"] = []
            row["events"].append({
                "from_state": prev_state,
                "to_state": state,
                "recorded_at": datetime.now(UTC).isoformat(),
            })

            try:
                self.applications_dir.mkdir(parents=True, exist_ok=True)
                yaml_content = yaml.safe_dump(row, allow_unicode=True, sort_keys=False)
                self._app_file(job_id).write_text(yaml_content, encoding="utf-8")
                self._write_pipeline_md()
            except Exception:
                if state == "applied":
                    job_obj = self.repo.get_job(job_id)
                    if job_obj:
                        job_obj.applied = False
                        self.repo.save_job(job_obj)
                raise
            return row

    def _write_pipeline_md(self) -> None:
        all_apps = self.list()
        states_order = [
            "discovered",
            "shortlisted",
            "drafting",
            "ready",
            "applied",
            "interviewing",
            "offer",
            "rejected",
            "withdrawn",
            "archived",
        ]
        lines = [
            "# Application Pipeline",
            f"*Updated at {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}*",
            "",
        ]
        apps_by_state: dict[str, list[dict[str, Any]]] = {st: [] for st in states_order}
        for app in all_apps:
            st = str(app["state"])
            if st in apps_by_state:
                apps_by_state[st].append(app)

        for st in states_order:
            items = apps_by_state[st]
            lines.append(f"## {st.title()} ({len(items)})")
            if not items:
                lines.append("*(none)*")
            else:
                for item in items:
                    job = self.repo.get_job(str(item["job_id"]))
                    title = job.title if job else "Unknown Title"
                    employer = job.employer if job else "Unknown Employer"
                    cv_info = f" [CV: {item['cv_version']}]" if item.get("cv_version") else ""
                    lines.append(f"- **{title}** at {employer} (`{item['job_id']}`){cv_info}")
            lines.append("")

        self.pipeline_file.write_text("\n".join(lines), encoding="utf-8")
