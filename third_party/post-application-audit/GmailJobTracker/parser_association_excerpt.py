from email_parser import EmailBodyParser, MetadataExtractor  # noqa: E402

def build_company_job_index(company, job_title, job_id):
    def normalize(text):
        if not text:
            return ""
        return re.sub(r"\s+", " ", text.strip().lower())
    return f"{normalize(company)}::{normalize(job_title)}::{normalize(job_id)}"


def _normalize_job_match_text(text: str | None) -> str:
    """Normalize job identifiers/titles for exact duplicate checks."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", str(text).strip().lower())


def _application_identity_matches(application_obj, company_obj, job_title: str, job_id: str) -> bool:
    """Return True when parsed application metadata matches an existing ThreadTracking."""
    if not application_obj or not company_obj or application_obj.company_id != company_obj.id:
        return False

    parsed_job_id = _normalize_job_match_text(job_id)
    existing_job_id = _normalize_job_match_text(application_obj.job_id)
    if parsed_job_id and existing_job_id:
        return parsed_job_id == existing_job_id

    parsed_job_title = _normalize_job_match_text(job_title)
    existing_job_title = _normalize_job_match_text(application_obj.job_title)
    if parsed_job_title and existing_job_title:
        return parsed_job_title == existing_job_title

    return False


def _should_enrich_existing_application(application_obj, company_obj, job_title: str, job_id: str) -> bool:
    """Return True when a same-thread application should enrich the existing record."""
    if _application_identity_matches(application_obj, company_obj, job_title, job_id):
        return True

    if not application_obj or not company_obj or application_obj.company_id != company_obj.id:
        return False

    parsed_job_title = _normalize_job_match_text(job_title)
    parsed_job_id = _normalize_job_match_text(job_id)
    if not parsed_job_title and not parsed_job_id:
        return False

    existing_job_title = _normalize_job_match_text(application_obj.job_title)
    existing_job_id = _normalize_job_match_text(application_obj.job_id)
    return not existing_job_title and not existing_job_id


def _find_existing_application_by_identity(
    company_obj,
    job_title: str,
    job_id: str,
    *,
    exclude_thread_ids=None,
    sent_date=None,
):
    """Find an existing application for the same company/job across threads."""
    if not company_obj:
        return None

    normalized_job_id = _normalize_job_match_text(job_id)
    normalized_job_title = _normalize_job_match_text(job_title)
    if not normalized_job_id and not normalized_job_title:
        return None

    queryset = ThreadTracking.objects.filter(company=company_obj).order_by("-sent_date", "-id")
    if exclude_thread_ids:
        queryset = queryset.exclude(thread_id__in=set(exclude_thread_ids))

    candidates = list(queryset)
    if sent_date:
        candidates = [
            candidate for candidate in candidates
            if not candidate.sent_date or candidate.sent_date <= sent_date
        ]
        recent_cutoff = sent_date - timedelta(days=3)
        recent_candidates = [
            candidate for candidate in candidates
            if candidate.sent_date and candidate.sent_date >= recent_cutoff
        ]
        if recent_candidates:
            candidates = recent_candidates

    for candidate in candidates:
        candidate_job_id = _normalize_job_match_text(candidate.job_id)
        if normalized_job_id and candidate_job_id == normalized_job_id:
            return candidate

    for candidate in candidates:
        candidate_job_title = _normalize_job_match_text(candidate.job_title)
        if normalized_job_title and candidate_job_title == normalized_job_title:
            return candidate

    return None


def _find_existing_milestone_application(
    company_obj,
    metadata,
    parsed_subject,
):
    """Find an existing application record for prescreen/interview milestones."""
    if not company_obj:
        return None

    thread_id = metadata.get("thread_id")
    if thread_id:
        application_obj = ThreadTracking.objects.filter(thread_id=thread_id).first()
        if application_obj:
            return application_obj

    exact_match = _find_existing_application_by_identity(
        company_obj,
        parsed_subject.get("job_title", "") if isinstance(parsed_subject, dict) else "",
        parsed_subject.get("job_id", "") if isinstance(parsed_subject, dict) else "",
        exclude_thread_ids={thread_id} if thread_id else None,
