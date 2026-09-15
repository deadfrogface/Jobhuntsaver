"""Local email classification with confidence (no cloud AI).

Primary phrase sets adapted from PBP ``detect_email_status`` / STATUS_PATTERNS
(MIT). English extras and false-rejection overrides adapted from
GmailJobTracker RuleClassifier early-detection ideas (MIT). Patterns stored
inline to avoid Django/json runtime coupling; GJT patterns.json is audit evidence.
"""

from __future__ import annotations

from dataclasses import dataclass

from integrations.email_normalize import normalize_umlauts


@dataclass(frozen=True)
class ClassificationResult:
    category: str  # confirmation|interview|offer|rejection|assessment|noise|other|ghosted
    confidence: float
    reasons: tuple[str, ...] = ()
    false_rejection_blocked: bool = False


# --- PBP STATUS_PATTERNS (adapted) + EN GJT-style phrases ---
STATUS_PATTERNS: dict[str, tuple[str, ...]] = {
    "confirmation": (
        "vielen dank fur ihre bewerbung",
        "vielen dank fuer ihre bewerbung",
        "bewerbung erhalten",
        "eingangsbestatigung",
        "eingangsbestaetigung",
        "wir haben ihre bewerbung erhalten",
        "ihre bewerbung ist bei uns eingegangen",
        "vielen dank fur deine bewerbung",
        "vielen dank fuer deine bewerbung",
        "thank you for your application",
        "application has been received",
        "we have received your application",
        "application received",
    ),
    "interview": (
        "vorstellungsgesprach",
        "vorstellungsgespraech",
        "gespraachstermin",
        "gesprächstermin",
        "terminvorschlag",
        "einladen zu einem gespräch",
        "einladen zu einem gespraech",
        "invite you to interview",
        "schedule an interview",
        "interview invitation",
        "phone screen",
        "schedule a call",
        "your interview is scheduled",
        "interview availability",
    ),
    "assessment": (
        "online-test",
        "online assessment",
        "coding challenge",
        "einstellungstest",
        "complete the assessment",
        "take-home assignment",
    ),
    "offer": (
        "stellenangebot",
        "job offer",
        "offer of employment",
        "wir mochten ihnen gerne eine stelle",
        "wir möchten ihnen gerne eine stelle",
        "anstellungsangebot",
        "congratulations.*offer",
    ),
    "rejection": (
        "leider mussen wir ihnen mitteilen",
        "leider muessen wir ihnen mitteilen",
        "absage",
        "nicht berucksichtigen",
        "nicht beruecksichtigen",
        "andere bewerberinnen",
        "andere bewerber",
        "we regret to inform",
        "unfortunately we will not",
        "not moving forward",
        "position has been filled",
        "decided to pursue other candidates",
        "will not be progressing",
    ),
}

# Scheduling / interview language that blocks weak rejection labels
# (GmailJobTracker rejection_override / scheduling_language idea).
REJECTION_OVERRIDE_PHRASES: tuple[str, ...] = (
    "terminvorschlag",
    "vorstellungsgesprach",
    "vorstellungsgespraech",
    "schedule an interview",
    "interview invitation",
    "please select a time",
    "calendar invite",
    "zoom meeting",
    "teams meeting",
    "availability for a call",
)

NOISE_PHRASES: tuple[str, ...] = (
    "unsubscribe",
    "newsletter",
    "job alert",
    "stellenangebot der woche",
    "recommended jobs",
    "marketing@",
    "noreply-promo",
)


def _hits(text_norm: str, patterns: tuple[str, ...]) -> list[str]:
    found: list[str] = []
    for p in patterns:
        # Support simple "a.*b" patterns without full regex engine exposure.
        if ".*" in p:
            left, _, right = p.partition(".*")
            if left in text_norm and right in text_norm:
                found.append(p)
        elif p in text_norm:
            found.append(p)
    return found


def classify_email(subject: str, body: str) -> ClassificationResult:
    """Classify hiring-related email. Conservative on rejection."""
    combined = normalize_umlauts(f"{subject or ''} {body or ''}")
    if not combined.strip():
        return ClassificationResult("other", 0.0, ("empty",))

    noise_hits = _hits(combined, NOISE_PHRASES)
    # Noise short-circuit only when no strong hiring signal.
    scores: dict[str, tuple[float, tuple[str, ...]]] = {}
    for category, patterns in STATUS_PATTERNS.items():
        hits = _hits(combined, patterns)
        if hits:
            conf = min(0.5 + 0.15 * len(hits), 0.98)
            scores[category] = (conf, tuple(hits[:5]))

    if not scores:
        if noise_hits:
            return ClassificationResult("noise", 0.7, tuple(noise_hits[:3]))
        return ClassificationResult("other", 0.2, ("no_pattern",))

    best_cat = max(scores.items(), key=lambda kv: kv[1][0])
    category, (confidence, reasons) = best_cat[0], best_cat[1]

    false_blocked = False
    if category == "rejection":
        overrides = _hits(combined, REJECTION_OVERRIDE_PHRASES)
        # Weak single-hit rejections are also blocked when interview language present.
        if overrides or (
            confidence < 0.8 and _hits(combined, STATUS_PATTERNS["interview"])
        ):
            false_blocked = True
            # Prefer interview if those phrases hit.
            if overrides or _hits(combined, STATUS_PATTERNS["interview"]):
                ih = _hits(combined, STATUS_PATTERNS["interview"]) or overrides
                return ClassificationResult(
                    "interview",
                    max(0.75, confidence),
                    tuple(ih[:5]),
                    false_rejection_blocked=True,
                )
            return ClassificationResult(
                "other",
                0.4,
                reasons + ("false_rejection_guard",),
                false_rejection_blocked=True,
            )

    if noise_hits and category == "rejection" and confidence < 0.75:
        return ClassificationResult("noise", 0.65, tuple(noise_hits[:3]))

    return ClassificationResult(
        category, confidence, reasons, false_rejection_blocked=false_blocked
    )
