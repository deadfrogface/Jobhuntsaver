"""Job normalization helpers."""

from core.deduplicator import make_job_id
from core.models import Job
from search.bundesagentur import _detect_remote


def test_job_from_dict_roundtrip():
    job = Job(id="1", title="A", match_reasons=["x"], rejection_reasons=["y"])
    data = job.to_dict()
    again = Job.from_dict(data)
    assert again.title == "A"
    assert again.match_reasons == ["x"]


def test_ba_remote_detection():
    assert _detect_remote({"homeofficemoeglich": True}, "Homeoffice 2 Tage") in ("hybrid", "remote")
    assert _detect_remote({}, "vor Ort in Düsseldorf") == "onsite"


def test_id_changes_with_source():
    assert make_job_id("indeed", "1") != make_job_id("linkedin", "1")
