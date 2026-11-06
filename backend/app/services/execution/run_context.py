from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse


class RunPreflightError(ValueError):
    pass


@dataclass(frozen=True)
class PlaywrightRunContext:
    application: str
    environment: str
    base_url: str
    artifact_root: Path
    headless: bool = False
    allow_mutations: bool = False
    full_page_screenshots: bool = True
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def __post_init__(self) -> None:
        parsed = urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise RunPreflightError("A valid HTTP(S) product starting URL is required.")
        if parsed.username or parsed.password:
            raise RunPreflightError("Credentials are not allowed in the product URL.")
        if self.environment.casefold() in {"production", "prod"}:
            raise RunPreflightError("Production execution is blocked.")
        if not re.fullmatch(r"[A-Za-z0-9_-]{8,80}", self.run_id):
            raise RunPreflightError("Run ID contains invalid characters.")

    @property
    def run_directory(self) -> Path:
        root = self.artifact_root.resolve()
        destination = (root / self.run_id).resolve()
        if root not in destination.parents:
            raise RunPreflightError("Run artifact directory escapes its configured root.")
        return destination

    def prepare(self) -> Path:
        directory = self.run_directory
        directory.mkdir(parents=True, exist_ok=False)
        return directory
