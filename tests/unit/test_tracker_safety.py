"""Synthetic regression checks for existing and new tracking safety gates."""
import pytest
import yaml

from mocnghe.applications.tracker import ApplicationTracker
from mocnghe.cv import CVService
from mocnghe.ingestion.manual import import_jd_text_with_status


def ready(repo, *, targeted=False):
    job, _ = import_jd_text_with_status(repo, 'Title: Synthetic safety job', source_identity='synthetic')
    cvs = CVService(repo)
    cv = cvs.create('v1', ['ev1'], language='en', job_id=job.job_id if targeted else None)
    cvs.approve(cv.id, cvs.content_hash(cv))
    tracker = ApplicationTracker(repo)
    tracker.transition(job.job_id, 'shortlisted')
    tracker.transition(job.job_id, 'drafting')
    tracker.transition(job.job_id, 'ready', cv_id=cv.id)
    return tracker, job, cv


def test_stale_untargeted_job_rejected_without_partial_write(repo):
    tracker, job, cv = ready(repo)
    job.title = "Changed"
    repo.save_job(job)
    with pytest.raises(ValueError, match='stale'):
        tracker.transition(job.job_id, 'applied', cv_id=cv.id, confirm=True)
    assert tracker.get(job.job_id)['state'] == 'ready'
    assert not repo.get_job(job.job_id).applied
    assert len(tracker.history(job.job_id)) == 3


def test_event_failure_rolls_back_flag_and_state(repo, monkeypatch):
    tracker, job, cv = ready(repo)
    # Simulate write failure during yaml dump
    def failing_write(*args, **kwargs):
        raise OSError("synthetic disk failure")
    monkeypatch.setattr(yaml, "safe_dump", failing_write)
    with pytest.raises(OSError, match="synthetic disk failure"):
        tracker.transition(job.job_id, 'applied', cv_id=cv.id, confirm=True)
    assert tracker.get(job.job_id)['state'] == 'ready'
    assert tracker.get(job.job_id)['applied_at'] is None
    assert not repo.get_job(job.job_id).applied


def test_duplicate_legacy_rows_fail_closed(repo):
    tracker, job, _ = ready(repo)
    # Corrupt yaml into bad data
    app_file = repo.applications_dir / f"{job.job_id}.yaml"
    app_file.write_text("not a dict\n", encoding="utf-8")
    with pytest.raises(ValueError, match='application not found'):
        tracker.transition(job.job_id, 'archived')


def test_snapshot_tampering_detected(repo):
    tracker, job, _ = ready(repo)
    app_file = repo.applications_dir / f"{job.job_id}.yaml"
    data = yaml.safe_load(app_file.read_text(encoding="utf-8"))
    data["submission_json"] = "{}"
    app_file.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(ValueError, match='hash'):
        tracker.get(job.job_id)


def test_duplicate_apply_and_terminal_reopen_rejected(repo):
    tracker, job, cv = ready(repo)
    tracker.transition(job.job_id, 'applied', cv_id=cv.id, confirm=True)
    with pytest.raises(ValueError, match='transition'):
        tracker.transition(job.job_id, 'applied', cv_id=cv.id, confirm=True)
    tracker.transition(job.job_id, 'rejected')
    tracker.transition(job.job_id, 'archived')
    with pytest.raises(ValueError, match='transition'):
        tracker.transition(job.job_id, 'shortlisted')
    assert repo.get_job(job.job_id).applied


def test_other_job_cv_rejected(repo):
    tracker, job, _ = ready(repo)
    other, _ = import_jd_text_with_status(repo, 'Title: Other synthetic job', source_identity='other')
    cvs = CVService(repo)
    cv = cvs.create('v1', ['ev1'], language='en', job_id=other.job_id)
    cvs.approve(cv.id, cvs.content_hash(cv))
    tracker.transition(job.job_id, 'drafting')
    with pytest.raises(ValueError, match='different'):
        tracker.transition(job.job_id, 'ready', cv_id=cv.id)
