from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from emailer import EmailConfig

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
JOBS_JSON_PATH = DATA_DIR / "jobs.json"
SESSION_STATE_PATH = DATA_DIR / "naukri_storage_state.json"

load_dotenv(ROOT_DIR / ".env")


def parse_csv(value: str, cast=str) -> list:
    if not value:
        return []
    return [cast(item.strip()) for item in value.split(",") if item.strip()]


class SearchConfig(BaseModel):
    titles: list[str] = Field(default_factory=lambda: ["Project Manager"])
    experiences: list[int] = Field(default_factory=lambda: [7])
    locations: list[str] = Field(default_factory=lambda: ["Bengaluru", "Chennai"])
    salary_band: str = "50-75 Lakhs"
    max_pages: int = 3
    max_jobs: int = 20
    max_jobs_per_search: int = 10


class AppConfig(BaseModel):
    email: str = ""
    password: str = ""
    groq_api_key: str = ""
    resume_path: str = ""
    headless: bool = False
    search: SearchConfig = Field(default_factory=SearchConfig)
    email_digest: EmailConfig | None = None


def load_config() -> AppConfig:
    email_enabled = os.getenv("EMAIL_DIGEST_ENABLED", "false").lower() == "true"
    return AppConfig(
        email=os.getenv("NAUKRI_EMAIL", ""),
        password=os.getenv("NAUKRI_PASSWORD", ""),
        groq_api_key=os.getenv("GROQ_API_KEY", ""),
        resume_path=os.getenv("RESUME_PATH", ""),
        headless=os.getenv("HEADLESS", "false").lower() == "true",
        search=SearchConfig(
            titles=parse_csv(os.getenv("SEARCH_TITLES", "Project Manager")),
            experiences=parse_csv(os.getenv("SEARCH_EXPERIENCES", "7"), int),
            locations=parse_csv(os.getenv("SEARCH_LOCATIONS", "Bengaluru,Chennai")),
            salary_band=os.getenv("SALARY_BAND", "50-75 Lakhs"),
            max_pages=int(os.getenv("MAX_PAGES", "3")),
            max_jobs=int(os.getenv("MAX_JOBS", "20")),
            max_jobs_per_search=int(os.getenv("MAX_JOBS_PER_SEARCH", "10")),
        ),
        email_digest=EmailConfig(
            enabled=email_enabled,
            smtp_host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_user=os.getenv("SMTP_USER", ""),
            smtp_password=os.getenv("SMTP_PASSWORD", ""),
            mail_from=os.getenv("MAIL_FROM", ""),
            mail_to=os.getenv("MAIL_TO", ""),
        )
        if email_enabled
        else None,
    )
