from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from mocnghe.applications.tracker import ApplicationTracker
from mocnghe.storage.repository import CareerRepository


def test_repository_locks_before_schema_migration(tmp_path):
    repo = CareerRepository(tmp_path / "fresh")
    repo.initialize()
    assert repo.lock_file.exists() or repo.workspace.exists()


def test_concurrent_first_use_on_fresh_database(tmp_path):
    for round_number in range(10):
        workspace = tmp_path / str(round_number)
        barrier = Barrier(4)

        def construct(_, workspace=workspace, barrier=barrier):
            repo = CareerRepository(workspace)
            barrier.wait(timeout=10)
            tracker = ApplicationTracker(repo)
            assert tracker.list() == []

        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(construct, range(4)))
        repo = CareerRepository(workspace)
        assert repo.applications_dir.exists()
