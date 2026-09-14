"""Fictional demo dataset for screenshots / showcase — never default for real users."""

from __future__ import annotations

from core.database import Database
from core.models import Job, JobStatus, utc_now_iso


DEMO_PROFILE = {
    "first_name": "Alex",
    "last_name": "Muster",
    "email": "alex.muster@example.com",
    "phone": "+49 30 1234567",
    "city": "Berlin",
    "titles": ["Office Manager", "Teamassistenz", "Projektkoordination"],
    "skills": ["MS Office", "Terminplanung", "Kommunikation"],
}


DEMO_JOBS = [
    {
        "title": "Office Manager (m/w/d)",
        "company": "Nordlicht Consulting GmbH",
        "city": "Berlin",
        "remote_type": "hybrid",
        "source": "bundesagentur",
        "match_score": 88,
        "status": JobStatus.NEW.value,
        "salary_text": "48.000–55.000 €",
        "description": "Organisation des Büroalltags, Terminplanung und Schnittstelle zur Geschäftsführung.",
        "match_reasons": ["Titel passt", "Hybrid in Pendelreichweite", "Office-Skills"],
    },
    {
        "title": "Teamassistenz Vertrieb",
        "company": "Havel Soft AG",
        "city": "Potsdam",
        "remote_type": "onsite",
        "source": "indeed",
        "match_score": 81,
        "status": JobStatus.QUEUED.value,
        "salary_text": "42.000 €",
        "description": "Unterstützung des Vertriebsteams, CRM-Pflege und Reiseorganisation.",
        "match_reasons": ["Assistenz-Erfahrung", "CRM-Nähe"],
    },
    {
        "title": "Projektkoordination Remote",
        "company": "Kiefer Digital UG",
        "city": "Remote DE",
        "remote_type": "remote",
        "source": "bundesagentur",
        "match_score": 76,
        "status": JobStatus.NEEDS_REVIEW.value,
        "salary_text": "50.000 €",
        "description": "Koordination interner Projekte, Status-Updates und Stakeholder-Kommunikation.",
        "match_reasons": ["Remote erlaubt", "Koordinationsprofil"],
    },
    {
        "title": "Empfangs- und Büromanagement",
        "company": "Spree Klinikverbund",
        "city": "Berlin",
        "remote_type": "onsite",
        "source": "indeed",
        "match_score": 72,
        "status": JobStatus.APPLIED.value,
        "salary_text": "39.000 €",
        "description": "Empfang, Dokumentenmanagement und Terminvergabe.",
        "match_reasons": ["Büroorganisation"],
    },
]


def seed_demo_database(db_path) -> int:
    """Insert fictional jobs into an isolated DB. Returns number of jobs written."""
    db = Database(db_path)
    now = utc_now_iso()
    count = 0
    for i, row in enumerate(DEMO_JOBS, start=1):
        job = Job(
            id=f"demo-{i}",
            title=row["title"],
            company=row["company"],
            city=row["city"],
            description=row["description"],
            url=f"https://example.com/jobs/demo-{i}",
            application_url=f"https://example.com/apply/demo-{i}",
            source=row["source"],
            remote_type=row["remote_type"],
            salary_text=row["salary_text"],
            match_score=row["match_score"],
            match_reasons=list(row["match_reasons"]),
            status=row["status"],
            discovered_at=now,
            published_at=now[:10],
            distance_km=8.5 if row["city"] == "Berlin" else 22.0,
        )
        db.upsert_job(job)
        count += 1
    return count
