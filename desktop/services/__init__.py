"""Central configuration service for the desktop GUI."""

from __future__ import annotations

import json
import shutil
from copy import deepcopy
from pathlib import Path
from typing import Any

from core.config import (
    AppConfig,
    CONFIG_DIR,
    load_config,
    save_config,
)
from desktop.paths import ensure_app_dirs, project_root


class ConfigService:
    """Load/save YAML config from AppData and expose it to the GUI."""

    def __init__(self) -> None:
        self.dirs = ensure_app_dirs()
        self.meta_path = self.dirs["root"] / "meta.json"
        self._config: AppConfig | None = None
        self._bootstrap_from_examples()

    @property
    def profile_path(self) -> Path:
        return self.dirs["config"] / "profile.yaml"

    @property
    def application_path(self) -> Path:
        return self.dirs["config"] / "application_profile.yaml"

    @property
    def settings_path(self) -> Path:
        return self.dirs["config"] / "settings.yaml"

    def _bootstrap_from_examples(self) -> None:
        """Seed AppData YAML from repo examples or existing local config once."""
        mapping = [
            (self.profile_path, "profile.yaml"),
            (self.application_path, "application_profile.yaml"),
            (self.settings_path, "settings.yaml"),
        ]
        for dest, name in mapping:
            if dest.exists():
                continue
            local = CONFIG_DIR / name
            example = CONFIG_DIR / f"{name}.example"
            src = local if local.exists() else example
            if src.exists():
                shutil.copy2(src, dest)

    def load(self) -> AppConfig:
        config = load_config(
            profile_path=self.profile_path,
            application_path=self.application_path,
            settings_path=self.settings_path,
            root=self.dirs["root"],
            strip_placeholders=True,
        )
        # Force absolute runtime paths under AppData
        config.settings.database_path = str(self.dirs["data"] / "jobs.db")
        config.settings.logs_dir = str(self.dirs["logs"])
        config.settings.browser_profile_dir = str(self.dirs["browser_profile"])
        tpl = Path(config.settings.cover_letter_template)
        if not tpl.is_absolute():
            bundled = project_root() / tpl
            if bundled.exists():
                config.settings.cover_letter_template = str(bundled)
        self._config = config
        # Persist cleaned profile if demo placeholders were stripped
        try:
            from core.config import strip_example_application, strip_example_placeholders
            from copy import deepcopy

            before = deepcopy(config.profile.qualifications)
            strip_example_placeholders(config.profile)
            after = config.profile.qualifications
            before_app = (config.application.first_name, config.application.email)
            strip_example_application(config.application)
            after_app = (config.application.first_name, config.application.email)
            if (
                before.skills != after.skills
                or before.software != after.software
                or before.languages != after.languages
                or before_app != after_app
            ):
                self.save(config)
        except Exception:
            pass
        return config

    @property
    def config(self) -> AppConfig:
        if self._config is None:
            return self.load()
        return self._config

    def reload(self) -> AppConfig:
        self._config = None
        return self.load()

    def save(self, config: AppConfig | None = None) -> AppConfig:
        config = config or self.config
        config.application.sync_address()
        # Keep runtime paths absolute in memory; persist portable relative names
        to_save = deepcopy(config)
        to_save.settings.database_path = "data/jobs.db"
        to_save.settings.logs_dir = "logs"
        to_save.settings.browser_profile_dir = "browser_profile"
        # Prefer relative template name in YAML
        tpl = Path(to_save.settings.cover_letter_template)
        if tpl.is_absolute():
            to_save.settings.cover_letter_template = "templates/cover_letter.txt"
        save_config(
            to_save,
            profile_path=self.profile_path,
            application_path=self.application_path,
            settings_path=self.settings_path,
        )
        self._config = self.load()
        return self._config

    def validate(self, config: AppConfig | None = None) -> list[str]:
        config = config or self.config
        errors: list[str] = []
        if config.profile.location.max_distance_km <= 0:
            errors.append("Pendeldistanz muss größer als 0 sein.")
        if config.settings.minimum_match_for_auto_apply < 0:
            errors.append("Mindest-Match darf nicht negativ sein.")
        if config.settings.max_applications_per_day < 1:
            errors.append("Max. Bewerbungen/Tag muss mindestens 1 sein.")
        mode = config.settings.mode
        if mode not in {
            "search_only",
            "review_before_submit",
            "fully_automatic",
        }:
            errors.append(f"Unbekannter Modus: {mode}")
        return errors

    def load_meta(self) -> dict[str, Any]:
        if not self.meta_path.exists():
            return {
                "first_run_completed": False,
                "last_search_run": "",
                "next_scheduled_run": "",
                "cv_variants": [],
            }
        try:
            return json.loads(self.meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"first_run_completed": False}

    def save_meta(self, meta: dict[str, Any]) -> None:
        self.meta_path.write_text(
            json.dumps(meta, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def mark_first_run_done(self) -> None:
        meta = self.load_meta()
        meta["first_run_completed"] = True
        self.save_meta(meta)

    def is_first_run(self) -> bool:
        return not bool(self.load_meta().get("first_run_completed"))

    def set_last_search(self, iso_ts: str) -> None:
        meta = self.load_meta()
        meta["last_search_run"] = iso_ts
        self.save_meta(meta)

    def get_window_state(self) -> dict[str, Any]:
        meta = self.load_meta()
        return dict(meta.get("window") or {})

    def save_window_state(
        self,
        *,
        width: int,
        height: int,
        x: int | None = None,
        y: int | None = None,
        maximized: bool = False,
    ) -> None:
        meta = self.load_meta()
        meta["window"] = {
            "width": int(width),
            "height": int(height),
            "x": x,
            "y": y,
            "maximized": bool(maximized),
        }
        self.save_meta(meta)

    def apply_safe_defaults(self, config: AppConfig) -> AppConfig:
        """First-run defaults from the conversion plan."""
        config.settings.mode = "search_only"
        config.settings.dry_run = True
        config.settings.automatic_submission = False
        config.settings.run_automatically = False
        config.settings.automation_paused = False
        return config

    def copy_cv_into_storage(self, source: Path, label: str = "Default CV") -> Path:
        source = Path(source)
        dest_dir = self.dirs["cvs"]
        dest = dest_dir / source.name
        if source.resolve() != dest.resolve():
            shutil.copy2(source, dest)
        meta = self.load_meta()
        variants = list(meta.get("cv_variants") or [])
        entry = {"label": label, "path": str(dest)}
        variants = [v for v in variants if v.get("path") != str(dest)]
        variants.append(entry)
        meta["cv_variants"] = variants
        self.save_meta(meta)
        cfg = self.config
        cfg.application.cv_path = str(dest)
        self.save(cfg)
        return dest
