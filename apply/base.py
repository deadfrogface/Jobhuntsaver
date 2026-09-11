"""Base application automation classes.

Adapted from AutoApply bot/apply/base.py (MIT).
"""

from __future__ import annotations

import logging
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.config import ApplicationProfile
from core.models import Job

logger = logging.getLogger("jobhuntsaver")

MAX_RETRIES = 2
RETRY_DELAYS = [3, 8]


@dataclass
class ApplyResult:
    success: bool
    error_message: str | None = None
    captcha_detected: bool = False
    manual_required: bool = False
    needs_review: bool = False
    login_required: bool = False
    dry_run_stopped: bool = False
    submitted: bool = False
    attempts: int = 1


class BaseApplier(ABC):
    ELEMENT_TIMEOUT = 5000
    NAV_TIMEOUT = 30000

    def __init__(self, page, *, dry_run: bool = True, submit: bool = False) -> None:
        self.page = page
        self.dry_run = dry_run
        self.submit = submit

    @abstractmethod
    def _do_apply(
        self,
        job: Job,
        resume_pdf_path: Path | None,
        cover_letter_text: str,
        profile: ApplicationProfile,
    ) -> ApplyResult:
        ...

    def apply(
        self,
        job: Job,
        resume_pdf_path: Path | None,
        cover_letter_text: str,
        profile: ApplicationProfile,
    ) -> ApplyResult:
        last_result: ApplyResult | None = None
        platform = self.__class__.__name__.replace("Applier", "")
        for attempt in range(1, MAX_RETRIES + 2):
            try:
                result = self._do_apply(job, resume_pdf_path, cover_letter_text, profile)
                result.attempts = attempt
                if result.success or result.captcha_detected or result.manual_required or result.needs_review:
                    return result
                last_result = result
                if result.error_message and any(
                    kw in result.error_message.lower()
                    for kw in ("form error", "validation", "required field", "unknown question")
                ):
                    return result
            except Exception as exc:
                logger.warning("%s attempt %d failed: %s", platform, attempt, exc)
                last_result = ApplyResult(success=False, error_message=str(exc), attempts=attempt)
            if attempt <= MAX_RETRIES:
                time.sleep(RETRY_DELAYS[min(attempt - 1, len(RETRY_DELAYS) - 1)])
        return last_result or ApplyResult(success=False, error_message="All retry attempts exhausted")

    def _human_type(self, locator, text: str) -> None:
        for char in text:
            locator.type(char)
            time.sleep(random.uniform(0.03, 0.08))

    def _random_pause(self, min_s: float = 0.5, max_s: float = 2.0) -> None:
        time.sleep(random.uniform(min_s, max_s))

    def _detect_captcha(self) -> bool:
        for selector in (
            "iframe[src*='captcha']",
            "iframe[src*='recaptcha']",
            "#captcha",
            ".g-recaptcha",
            "[data-sitekey]",
        ):
            if self.page.query_selector(selector):
                return True
        return False

    def _safe_goto(self, url: str, **kwargs) -> None:
        kwargs.setdefault("wait_until", "domcontentloaded")
        kwargs.setdefault("timeout", self.NAV_TIMEOUT)
        self.page.goto(url, **kwargs)

    def _wait_and_query(self, selector: str, timeout: int | None = None) -> Any:
        timeout = timeout or self.ELEMENT_TIMEOUT
        try:
            self.page.wait_for_selector(selector, timeout=timeout, state="visible")
            return self.page.query_selector(selector)
        except Exception:
            return None

    def _safe_fill(self, selector: str, value: str, clear_first: bool = True) -> bool:
        if not value:
            return False
        el = self.page.query_selector(selector)
        if not el or not el.is_visible():
            return False
        if clear_first:
            try:
                current = el.input_value()
            except Exception:
                current = ""
            if current == value:
                return False
            if current:
                el.fill("")
        try:
            if not el.input_value():
                self._human_type(el, value)
                self._random_pause(0.2, 0.5)
                return True
        except Exception:
            el.fill(value)
            return True
        return False

    def _fill_identity_fields(
        self,
        profile: ApplicationProfile,
        *,
        first_name: str = "input[name*='first'], input[id*='first']",
        last_name: str = "input[name*='last_name' i], input[name*='lastName'], input[name*='nachname' i], input[id*='last']",
        email: str = "input[type='email']",
        phone: str = "input[type='tel']",
        full_name: str | None = None,
        linkedin: str | None = None,
        resume_pdf_path: Path | None = None,
        file_selectors: str | list[str] | None = "input[type='file']",
    ) -> bool:
        """Fill common contact fields; return False only if CV upload was requested and failed."""
        if first_name:
            self._safe_fill(first_name, profile.first_name)
        if last_name:
            self._safe_fill(last_name, profile.last_name)
        if full_name:
            self._safe_fill(full_name, profile.full_name)
        if email:
            self._safe_fill(email, profile.email)
        if phone:
            self._safe_fill(phone, profile.phone_full)
        if linkedin and profile.linkedin_url:
            self._safe_fill(linkedin, profile.linkedin_url)
        if resume_pdf_path and file_selectors:
            return self._safe_upload(resume_pdf_path, file_selectors)
        return True

    def _safe_upload(self, resume_path: Path, selectors: str | list[str]) -> bool:
        if isinstance(selectors, str):
            selectors = [selectors]
        for selector in selectors:
            file_input = self.page.query_selector(selector)
            if file_input:
                try:
                    file_input.set_input_files(str(resume_path))
                    self._random_pause(1, 2)
                    return True
                except Exception as exc:
                    logger.warning("Upload failed via %s: %s", selector, exc)
        return False

    def _safe_click(self, selector: str, timeout: int | None = None) -> bool:
        el = self._wait_and_query(selector, timeout=timeout or 3000)
        if el and el.is_visible():
            el.click()
            return True
        return False

    def _fill_cover_letter(
        self,
        text: str,
        selectors: str | list[str] | None = None,
    ) -> bool:
        """Fill the first visible cover-letter textarea matching ``selectors``."""
        if not text:
            return False
        if selectors is None:
            selectors = [
                "textarea[name*='cover_letter']",
                "textarea[id*='cover_letter']",
                "textarea[name*='cover']",
                "textarea[id*='cover']",
                "#cover_letter",
                "textarea",
            ]
        if isinstance(selectors, str):
            selectors = [selectors]
        for selector in selectors:
            ta = self.page.query_selector(selector)
            if not ta or not ta.is_visible():
                continue
            try:
                if ta.input_value():
                    return False
            except Exception:
                pass
            ta.fill(text)
            return True
        return False

    def _unknown_required_fields(
        self,
        profile: ApplicationProfile,
        *,
        skip_tokens: tuple[str, ...] = (
            "first",
            "last",
            "email",
            "phone",
            "resume",
            "cover",
            "file",
            "cv",
        ),
    ) -> list[str]:
        """Return required empty fields that are not identity/CV and not in profile.answers."""
        unknown: list[str] = []
        for el in self.page.query_selector_all(
            "input[required], textarea[required], select[required]"
        ):
            try:
                name = (el.get_attribute("name") or el.get_attribute("id") or "").lower()
                if not name:
                    continue
                if any(k in name for k in skip_tokens):
                    continue
                answered = False
                for key, val in profile.answers.items():
                    if key.lower() in name and val:
                        attr_name = el.get_attribute("name")
                        if attr_name:
                            self._safe_fill(f"[name='{attr_name}']", val)
                        answered = True
                        break
                if answered:
                    continue
                try:
                    if el.input_value():
                        continue
                except Exception:
                    pass
                unknown.append(name)
            except Exception:
                continue
        return unknown

    def _unknown_required_labels(
        self,
        profile: ApplicationProfile,
        *,
        skip_tokens: tuple[str, ...] = ("name", "email", "phone", "resume", "cover"),
    ) -> list[str]:
        """Ashby-style: required labels marked with ``*`` that lack known answers."""
        unknown: list[str] = []
        for label in self.page.query_selector_all("label"):
            try:
                label_text = label.inner_text().strip().lower()
            except Exception:
                continue
            matched = False
            for key, value in profile.answers.items():
                if key.lower().replace("_", " ") in label_text and value:
                    label_for = label.get_attribute("for")
                    if label_for:
                        self._safe_fill(f"#{label_for}", value)
                        matched = True
                        break
            if matched:
                continue
            if "*" not in label_text:
                continue
            if any(x in label_text for x in skip_tokens):
                continue
            unknown.append(label_text[:80])
        return unknown

    def _maybe_submit(self, submit_selector: str) -> ApplyResult:
        """Central hard guard: never click final submit in dry_run / non-submit mode."""
        if self.dry_run or not self.submit:
            logger.info(
                "TEST MODE: skipped final submit "
                "(dry_run=%s, submit=%s, selector=%s)",
                self.dry_run,
                self.submit,
                submit_selector,
            )
            return ApplyResult(
                success=True,
                dry_run_stopped=True,
                submitted=False,
                error_message="Stopped before submit (dry_run / review mode)",
            )
        btn = self._wait_and_query(submit_selector, timeout=5000)
        if not btn:
            return ApplyResult(
                success=False,
                manual_required=True,
                needs_review=True,
                error_message="Submit button not found",
            )
        btn.click()
        self._random_pause(2, 4)
        return ApplyResult(success=True, submitted=True)
