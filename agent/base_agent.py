from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from playwright.async_api import BrowserContext, Page, TimeoutError, async_playwright

from config import AppConfig, DATA_DIR, JOBS_JSON_PATH
from groq_helper import GroqAnswerer
from resume_text import extract_resume_text
from emailer import send_company_site_digest
from storage import write_jobs_snapshot

@dataclass
class JobRecord:
    title: str
    company: str
    location: str
    jobExperienceReq: str
    salary: str
    searchTitle: str
    searchExperience: int
    searchLocation: str
    jobUrl: str
    applyType: str
    applied: bool
    status: str
    notes: str
    resumeUpdated: bool = False
    postedDate: str = ""
    lastCheckedAt: str = ""

class BaseJobAgent:
    def __init__(self, config: AppConfig):
        self.config = config
        self.resume_text = extract_resume_text(config.resume_path)
        self.answerer = GroqAnswerer(
            api_key=config.groq_api_key,
            candidate_profile=self._candidate_profile_text(),
        )
        self.jobs: list[JobRecord] = []
        self.profile_resume_refreshed = False
        self.session_state_path = DATA_DIR / f"{self.site_name}_storage_state.json"

    @property
    def site_name(self) -> str:
        raise NotImplementedError("Subclasses must define site_name")

    def _candidate_profile_text(self) -> str:
        resume_excerpt = (self.resume_text or "")[:6000]
        return f"""
Name: A Sivakumar
Preferred roles: {", ".join(self.config.search.titles)}
Preferred locations: {", ".join(self.config.search.locations)}
Target salary band: {self.config.search.salary_band}
Resume path: {self.config.resume_path}
Notice period: Immediate or less than 15 days

Resume text (excerpt):
{resume_excerpt}
"""

    async def run(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=self.config.headless,
                slow_mo=120,
                args=["--disable-blink-features=AutomationControlled"],
            )
            storage_state = str(self.session_state_path) if self.session_state_path.exists() else None
            context = await browser.new_context(
                viewport={"width": 1440, "height": 960},
                locale="en-IN",
                timezone_id="Asia/Kolkata",
                storage_state=storage_state,
            )
            await context.add_init_script(
                """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-IN', 'en']});
                window.chrome = { runtime: {} };
                """
            )
            page = await context.new_page()

            try:
                await self.ensure_logged_in(page)
                self.profile_resume_refreshed = await self._update_profile_resume_once(page)
                print(f"[{self.site_name}] Profile resume update attempted. Success={self.profile_resume_refreshed}")
                
                for title in self.config.search.titles:
                    for experience in self.config.search.experiences:
                        for location in self.config.search.locations:
                            await self.process_search(page, title, experience, location)
                            if len(self.jobs) >= self.config.search.max_jobs:
                                break
                        if len(self.jobs) >= self.config.search.max_jobs:
                            break
                    if len(self.jobs) >= self.config.search.max_jobs:
                        break
            finally:
                await self._save_session(context)
                await browser.close()

        self._save_jobs()
        
        if self.config.email_digest:
            jobs_payload = [asdict(job) for job in self.jobs]
            try:
                sent = send_company_site_digest(self.config.email_digest, jobs_payload, self.site_name)
                print(f"[{self.site_name}] Company-site email digest sent={sent}")
            except Exception as exc:
                print(f"[{self.site_name}] Company-site email digest failed: {exc}")

    def _save_jobs(self) -> None:
        jobs_payload = [asdict(job) for job in self.jobs]
        write_jobs_snapshot(JOBS_JSON_PATH, jobs_payload)

    async def _save_session(self, context: BrowserContext) -> None:
        await context.storage_state(path=str(self.session_state_path))

    async def ensure_logged_in(self, page: Page) -> None:
        raise NotImplementedError

    async def _update_profile_resume_once(self, page: Page) -> bool:
        return False

    async def process_search(self, page: Page, title: str, experience: int, location: str) -> None:
        raise NotImplementedError

    async def _safe_goto(self, page: Page, url: str, retries: int = 3) -> None:
        last_error = None
        for attempt in range(1, retries + 1):
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                return
            except Exception as exc:
                last_error = exc
                message = str(exc)
                print(f"[{self.site_name}] Navigation retry {attempt}/{retries} for {url}: {message}")
                await asyncio.sleep(2)
        if last_error:
            print(f"[{self.site_name}] All navigation retries failed for {url}")

    async def _is_visible(self, page: Page, selector: str, timeout: int = 1200) -> bool:
        try:
            locator = page.locator(selector).first
            return await locator.is_visible(timeout=timeout)
        except Exception:
            return False

    async def _safe_inner_text(self, locator) -> str:
        try:
            if await locator.count() > 0:
                return (await locator.inner_text()).strip()
        except Exception:
            pass
        return ""

    async def _first_visible_locator(self, page: Page, selectors: list[str], timeout: int = 5000):
        last_error = None
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                await locator.wait_for(state="visible", timeout=timeout)
                return locator
            except Exception as exc:
                last_error = exc
                continue
        if last_error:
            raise last_error
        raise TimeoutError("No visible locator found")

    async def _fill_first_visible(self, page: Page, selectors: list[str], value: str) -> None:
        locator = await self._first_visible_locator(page, selectors)
        await locator.click()
        await locator.fill(value)

    async def _upload_resume_if_possible(self, page: Page) -> bool:
        if not self.config.resume_path or not Path(self.config.resume_path).exists():
            print(f"Resume path does not exist or not provided: {self.config.resume_path}")
            return False
            
        selectors_to_try = [
            "input#attachCV",
            "input[id*='attachCV']",
            "input[type='file'][accept*='pdf']",
            "input[type='file']",
            "input[type='file'][name='resume']"
        ]
        
        for selector in selectors_to_try:
            try:
                locator = page.locator(selector).first
                if await locator.count():
                    print(f"[{self.site_name}] Found resume input using {selector}, attempting upload...")
                    await locator.set_input_files(self.config.resume_path)
                    await asyncio.sleep(5)
                    return True
            except Exception as e:
                print(f"[{self.site_name}] Failed setting input files for {selector}: {e}")
                continue
                
        print(f"[{self.site_name}] Could not find any resume upload input element.")
        return False
