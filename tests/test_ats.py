"""ATS detection tests."""

from apply.detector import ATSDetector


def test_detect_known_ats():
    assert ATSDetector.detect("https://boards.greenhouse.io/acme/jobs/1") == "greenhouse"
    assert ATSDetector.detect("https://jobs.lever.co/acme/abc") == "lever"
    assert ATSDetector.detect("https://company.myworkdayjobs.com/en-US/careers") == "workday"
    assert ATSDetector.detect("https://jobs.ashbyhq.com/acme") == "ashby"
    assert ATSDetector.detect("https://acme.jobs.personio.de/job/123") == "personio"
    assert ATSDetector.detect("https://www.stepstone.de/stellenangebote--x") == "stepstone"
    assert ATSDetector.detect("https://jobs.smartrecruiters.com/x") == "smartrecruiters"
    assert ATSDetector.detect("https://careerxxx.successfactors.eu/career") == "successfactors"
    assert ATSDetector.detect("https://example.com/jobs/1") == "unknown"
