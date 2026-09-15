from pathlib import Path

from app.config import Settings
from app.models import ScenePlan
from app.jobs import JobStore


def test_scene_requires_ten_seconds():
    try:
        ScenePlan(index=1, duration_seconds=9, visual_prompt="a" * 20, audio_prompt="no speech natural ambience", transition_note="connect")
    except ValueError:
        return
    raise AssertionError("invalid scene duration accepted")


def test_job_state_machine(tmp_path: Path):
    store = JobStore(tmp_path)
    job = store.create("village recipe")
    store.transition(job["id"], __import__("app.models", fromlist=["JobState"]).JobState.PLANNING)
    assert store.get(job["id"])["state"] == "planning"
