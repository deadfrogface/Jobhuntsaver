"""Günther service facade — wires provider, validation, intelligence."""

from __future__ import annotations

import json
import threading
from typing import Any

from guenther.contracts import GuentherEnvelope
from guenther.fallbacks import fallback_envelope
from guenther.hardware import HardwareTier, detect_hardware, graceful_model_fallback
from guenther.inference import InferenceController
from guenther.model_manager import ModelManager, default_models_dir
from guenther.privacy import log_event
from guenther.prompts import SCHEMA_HINTS, build_layers
from guenther.provider import GenerationRequest, LocalAIProvider, ProviderStatus
from guenther.runtime.heuristic_provider import HeuristicProvider
from guenther.runtime.llama_cpp_provider import LlamaCppProvider
from guenther.runtime.null_provider import NullProvider
from guenther.runtime.ollama_provider import OllamaProvider
from guenther.validation import (
    envelope_from_model,
    parse_contract,
    validate_association,
    validate_cv_extract,
    validate_email_class,
    validate_evidence_assist,
    validate_interview_prep,
    validate_job_analysis,
    validate_writing,
)


class GuentherService:
    def __init__(
        self,
        *,
        enabled: bool = False,
        model: str = "auto",
        prefer_ollama: bool = False,
        allow_heuristic_when_no_llm: bool = True,
    ) -> None:
        self.enabled = enabled
        self.model_pref = model
        self.hardware = detect_hardware()
        self.models_dir = default_models_dir()
        self.manager = ModelManager(self.models_dir)
        self.provider: LocalAIProvider = self._select_provider(prefer_ollama=prefer_ollama)
        if allow_heuristic_when_no_llm and not self.provider.is_available():
            # Still prefer null for "LLM missing" honesty when enabled+want LLM;
            # heuristic is used as assist layer only when explicitly allowed.
            self._heuristic = HeuristicProvider()
        else:
            self._heuristic = HeuristicProvider() if allow_heuristic_when_no_llm else None
        ram_tight = self.hardware.tier == HardwareTier.LIGHT
        self.inference = InferenceController(self.provider, ram_tight=ram_tight)
        self._lock = threading.Lock()

    def _select_provider(self, *, prefer_ollama: bool) -> LocalAIProvider:
        if prefer_ollama:
            ollama = OllamaProvider()
            if ollama.is_available():
                return ollama
        llama = LlamaCppProvider(self.models_dir)
        if llama.is_available():
            return llama
        return NullProvider(ProviderStatus.NOT_INSTALLED)

    def ensure_model_loaded(self) -> ProviderStatus:
        if not self.enabled:
            return ProviderStatus.UNAVAILABLE
        mid = graceful_model_fallback(self.hardware.tier, self.model_pref)
        if self.provider.provider_id == "llama_cpp" and not self.manager.is_installed(mid):
            # try any installed
            installed = [m["id"] for m in self.manager.list_catalog() if m["installed"]]
            if not installed:
                return ProviderStatus.MODEL_MISSING
            mid = installed[0]
        return self.provider.load_model(mid)

    def status_summary(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "provider": self.provider.provider_id,
            "provider_status": self.provider.status().value,
            "model_pref": self.model_pref,
            "hardware_tier": self.hardware.tier.value,
            "ram_gb": self.hardware.ram_gb,
            "recommended_model": self.hardware.recommended_model_id,
            "models_dir": str(self.models_dir),
        }

    def _generate_validated(
        self,
        *,
        capability: str,
        schema_name: str,
        task: str,
        trusted: str,
        untrusted: str,
        use_heuristic_fallback: bool = True,
        timeout_s: float = 120.0,
    ) -> tuple[Any | None, GuentherEnvelope]:
        if not self.enabled:
            return None, fallback_envelope(capability, reason="disabled")

        system, trusted_b, untrusted_b = build_layers(
            task=task,
            schema_hint=SCHEMA_HINTS.get(schema_name, "{}"),
            trusted=trusted,
            untrusted=untrusted,
        )
        req = GenerationRequest(
            system=system,
            trusted=trusted_b,
            untrusted=untrusted_b,
            schema_name=schema_name,
            timeout_s=timeout_s,
        )

        status = self.ensure_model_loaded()
        result = None
        if status == ProviderStatus.READY or self.provider.status() == ProviderStatus.READY:
            result = self.provider.generate(req)
        elif use_heuristic_fallback and self._heuristic is not None:
            log_event("heuristic_fallback", capability=capability, status=status.value)
            result = self._heuristic.generate(req)
        else:
            return None, fallback_envelope(
                capability,
                reason=status.value,
                provider_status=status.value,
            )

        if not result.ok:
            if use_heuristic_fallback and self._heuristic and result.provider_id != "heuristic":
                result = self._heuristic.generate(req)
            if not result.ok:
                return None, fallback_envelope(
                    capability,
                    reason=result.error_code or result.status.value,
                    provider_status=result.status.value,
                    model_id=result.model_id,
                )

        model = parse_contract(schema_name, result.parsed or result.text)
        if model is None:
            return None, fallback_envelope(
                capability,
                reason="invalid_output",
                provider_status=result.status.value,
                model_id=result.model_id,
            )
        return model, envelope_from_model(
            capability=capability,
            model=model,
            ok=True,
            provider_status=result.status.value,
            model_id=result.model_id,
            validated=False,
        )

    # --- Public intelligence APIs ---

    def suggest_cv_extract(
        self, cv_text: str, *, manual_profile: dict[str, Any] | None = None
    ) -> GuentherEnvelope:
        model, env = self._generate_validated(
            capability="cv_extract",
            schema_name="cv_extract",
            task="Extrahiere nur im Text belegte CV-Fakten als JSON.",
            trusted=json.dumps({"manual": manual_profile or {}}, ensure_ascii=False),
            untrusted=cv_text[:20000],
        )
        if model is None:
            return env
        from guenther.contracts import CVExtractSuggestion

        assert isinstance(model, CVExtractSuggestion)
        model, notes = validate_cv_extract(model, cv_text=cv_text, manual_profile=manual_profile)
        return envelope_from_model(
            capability="cv_extract",
            model=model,
            ok=True,
            provider_status=env.provider_status,
            model_id=env.model_id,
            safety_notes=notes,
            validated=True,
        )

    def suggest_job_analysis(self, job_text: str) -> GuentherEnvelope:
        model, env = self._generate_validated(
            capability="job_analysis",
            schema_name="job_analysis",
            task="Extrahiere Anforderungen nur aus dem StellenText.",
            trusted="",
            untrusted=job_text[:20000],
        )
        if model is None:
            return env
        from guenther.contracts import JobAnalysisSuggestion

        assert isinstance(model, JobAnalysisSuggestion)
        model, notes = validate_job_analysis(model, job_text=job_text)
        return envelope_from_model(
            capability="job_analysis",
            model=model,
            ok=True,
            provider_status=env.provider_status,
            model_id=env.model_id,
            safety_notes=notes,
            validated=True,
        )

    def suggest_evidence_assist(
        self,
        *,
        profile_text: str,
        job_text: str,
        existing_evidence: list[dict[str, Any]] | None = None,
    ) -> GuentherEnvelope:
        trusted = json.dumps({"evidence": existing_evidence or []}, ensure_ascii=False)
        model, env = self._generate_validated(
            capability="evidence_assist",
            schema_name="evidence_assist",
            task="Bewerte Evidenz; niemals NOT_SUPPORTED zu DIRECT ohne Profilbeleg.",
            trusted=f"{trusted}\nPROFILE:\n{profile_text[:8000]}",
            untrusted=job_text[:12000],
        )
        if model is None:
            return env
        from guenther.contracts import EvidenceAssistSuggestion

        assert isinstance(model, EvidenceAssistSuggestion)
        model, notes = validate_evidence_assist(
            model,
            profile_text=profile_text,
            job_text=job_text,
            existing_evidence=existing_evidence,
        )
        return envelope_from_model(
            capability="evidence_assist",
            model=model,
            ok=True,
            provider_status=env.provider_status,
            model_id=env.model_id,
            safety_notes=notes,
            validated=True,
        )

    def suggest_email_class(
        self,
        subject: str,
        body: str,
        *,
        deterministic_category: str | None = None,
        deterministic_false_rejection_blocked: bool = False,
    ) -> GuentherEnvelope:
        model, env = self._generate_validated(
            capability="email_class",
            schema_name="email_class",
            task="Klassifiziere Bewerbungs-E-Mail; bei Zweifel niedrige Konfidenz.",
            trusted=json.dumps(
                {
                    "deterministic_category": deterministic_category,
                    "false_rejection_blocked": deterministic_false_rejection_blocked,
                },
                ensure_ascii=False,
            ),
            untrusted=f"subject: {subject}\nbody: {body[:12000]}",
        )
        if model is None:
            return env
        from guenther.contracts import EmailClassSuggestion

        assert isinstance(model, EmailClassSuggestion)
        model, notes = validate_email_class(
            model,
            deterministic_category=deterministic_category,
            deterministic_false_rejection_blocked=deterministic_false_rejection_blocked,
        )
        return envelope_from_model(
            capability="email_class",
            model=model,
            ok=True,
            provider_status=env.provider_status,
            model_id=env.model_id,
            safety_notes=notes,
            validated=True,
        )

    def suggest_association(
        self,
        *,
        sender: str,
        subject: str,
        cases: list[dict[str, Any]],
        deterministic_case_id: str | None = None,
        deterministic_ambiguous: bool = False,
    ) -> GuentherEnvelope:
        model, env = self._generate_validated(
            capability="association",
            schema_name="association",
            task="Ordne E-Mail einem Fall zu; im Zweifel ambiguous=true und case_id=null.",
            trusted=json.dumps({"cases": cases[:50]}, ensure_ascii=False),
            untrusted=f"sender: {sender}\nsubject: {subject}",
        )
        if model is None:
            return env
        from guenther.contracts import AssociationSuggestion

        assert isinstance(model, AssociationSuggestion)
        known = {str(c.get("id") or "") for c in cases}
        model, notes = validate_association(
            model, known_case_ids=known, deterministic_ambiguous=deterministic_ambiguous
        )
        # Deterministic unambiguous high-confidence link wins over weak LLM
        if deterministic_case_id and not deterministic_ambiguous:
            if model.case_id and model.case_id != deterministic_case_id:
                notes.append("deterministic_case_preferred")
                model.case_id = deterministic_case_id
                model.ambiguous = False
        return envelope_from_model(
            capability="association",
            model=model,
            ok=True,
            provider_status=env.provider_status,
            model_id=env.model_id,
            safety_notes=notes,
            validated=True,
        )

    def suggest_writing(
        self,
        *,
        profile_text: str,
        job_text: str,
        draft_kind: str = "cover_letter",
        seed_body: str = "",
    ) -> GuentherEnvelope:
        model, env = self._generate_validated(
            capability="writing",
            schema_name="writing",
            task=f"Verbessere {draft_kind}; erfinde keine Fakten.",
            trusted=f"PROFILE:\n{profile_text[:8000]}\nSEED:\n{seed_body[:4000]}",
            untrusted=f"JOB:\n{job_text[:8000]}",
        )
        if model is None:
            return env
        from guenther.contracts import WritingSuggestion

        assert isinstance(model, WritingSuggestion)
        model, notes = validate_writing(model, profile_text=profile_text, job_text=job_text)
        return envelope_from_model(
            capability="writing",
            model=model,
            ok=True,
            provider_status=env.provider_status,
            model_id=env.model_id,
            safety_notes=notes,
            validated=True,
        )

    def suggest_interview_prep(
        self,
        *,
        profile_text: str,
        job_text: str,
        evidence: list[dict[str, Any]] | None = None,
    ) -> GuentherEnvelope:
        ev_text = json.dumps(evidence or [], ensure_ascii=False)
        model, env = self._generate_validated(
            capability="interview_prep",
            schema_name="interview_prep",
            task="Interview-Prep nur aus Evidenz/Profil; keine erfundenen Erfolge.",
            trusted=f"PROFILE:\n{profile_text[:8000]}\nEVIDENCE:\n{ev_text[:8000]}",
            untrusted=f"JOB:\n{job_text[:8000]}",
        )
        if model is None:
            return env
        from guenther.contracts import InterviewPrepSuggestion

        assert isinstance(model, InterviewPrepSuggestion)
        model, notes = validate_interview_prep(
            model, profile_text=profile_text, job_text=job_text, evidence_text=ev_text
        )
        return envelope_from_model(
            capability="interview_prep",
            model=model,
            ok=True,
            provider_status=env.provider_status,
            model_id=env.model_id,
            safety_notes=notes,
            validated=True,
        )


_SERVICE: GuentherService | None = None
_SERVICE_LOCK = threading.Lock()


def get_guenther_service(
    *,
    enabled: bool | None = None,
    model: str | None = None,
    refresh: bool = False,
) -> GuentherService:
    global _SERVICE
    with _SERVICE_LOCK:
        if _SERVICE is None or refresh:
            _SERVICE = GuentherService(
                enabled=bool(enabled) if enabled is not None else False,
                model=model or "auto",
            )
        else:
            if enabled is not None:
                _SERVICE.enabled = bool(enabled)
            if model is not None:
                _SERVICE.model_pref = model
        return _SERVICE
