import pytest

from mocnghe.applications.tracker import ApplicationTracker
from mocnghe.cv import CVService
from mocnghe.ingestion.manual import import_jd_text_with_status


@pytest.mark.parametrize('change', ['profile_hash', 'job_title'])
def test_change_after_validation_is_rejected(repo, monkeypatch, change):
    job, _ = import_jd_text_with_status(repo, 'Title: Synthetic race', source_identity='race')
    cvs = CVService(repo)
    cv = cvs.create('v1', ['ev1'], language='en', job_id=job.job_id)
    cvs.approve(cv.id, cvs.content_hash(cv))
    tracker = ApplicationTracker(repo)
    tracker.transition(job.job_id, 'shortlisted')
    tracker.transition(job.job_id, 'drafting')
    original = CVService.approved

    def racing_approved(self, cv_id):
        result = original(self, cv_id)
        original_get_profile = repo.get_profile_version
        original_get_job = repo.get_job
        def racing_get_profile(version):
            if change == 'profile_hash':
                raise ValueError("stale canonical profile")
            return original_get_profile(version)
        def racing_get_job(jid):
            if change == 'job_title':
                j = original_get_job(jid)
                if j:
                    j.title = "Changed"
                return j
            return original_get_job(jid)
        monkeypatch.setattr(repo, 'get_profile_version', racing_get_profile)
        monkeypatch.setattr(repo, 'get_job', racing_get_job)
        return result

    monkeypatch.setattr(CVService, 'approved', racing_approved)
    with pytest.raises(ValueError, match='canonical'):
        tracker.transition(job.job_id, 'ready', cv_id=cv.id)
    assert tracker.get(job.job_id)['state'] == 'drafting'
    assert not repo.get_job(job.job_id).applied


def test_migration_locks_before_column_discovery(repo, monkeypatch):
    assert repo.lock_file is not None
