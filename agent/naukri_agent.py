from __future__ import annotations

import asyncio
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from playwright.async_api import Page, TimeoutError

from base_agent import BaseJobAgent, JobRecord
from config import JOBS_JSON_PATH
from emailer import send_company_site_digest
from storage import write_jobs_snapshot


class NaukriPlaywrightAgent(BaseJobAgent):
    @property
    def site_name(self) -> str:
        return "naukri"

    async def run(self) -> None:
        await super().run()


    async def ensure_logged_in(self, page: Page) -> None:
        await self._safe_goto(page, "https://www.naukri.com/mnjuser/homepage")
        await asyncio.sleep(3)
        if await self._has_authenticated_session(page):
            print("Session already logged in. Proceeding...")
            return

        print("Session not logged in. Opening login flow...")
        await self._safe_goto(page, "https://www.naukri.com/")
        await asyncio.sleep(3)
        await self._dismiss_popups(page)

        for selector in [
            "button:has-text('Login')",
            "a:has-text('Login')",
            "[title='Jobseeker Login']",
        ]:
            try:
                locator = page.locator(selector).first
                if await locator.is_visible(timeout=1500):
                    print(f"Clicking login trigger: {selector}")
                    await locator.click()
                    await asyncio.sleep(2)
                    break
            except Exception:
                continue
        else:
            print("Homepage login trigger not found. Opening direct login page.")
            await self._safe_goto(page, "https://www.naukri.com/nlogin/login")
            await asyncio.sleep(2)

        await self._fill_first_visible(
            page,
            [
                "input[placeholder*='Email']",
                "input[placeholder*='Username']",
                "input[type='email']",
                "input[name='username']",
            ],
            self.config.email,
        )
        print("Filled email/username.")
        await self._fill_first_visible(
            page,
            [
                "input[type='password']",
                "input[placeholder*='Password']",
                "input[name='password']",
            ],
            self.config.password,
        )
        print("Filled password.")

        submit_clicked = False
        for selector in [
            "button:has-text('Login')",
            "button[type='submit']",
            "button:has-text('Continue')",
            "button.btn-primary",
            "button.res-OT-login-btn",
            "button[formaction*='login']",
            "button:has-text('Submit')",
        ]:
            try:
                locator = page.locator(selector).first
                if await locator.is_visible(timeout=1500):
                    print(f"Clicking login submit: {selector}")
                    await locator.click()
                    submit_clicked = True
                    await asyncio.sleep(8)
                    break
            except Exception:
                continue

        if not submit_clicked:
            print("Login submit button was not confidently clickable. Trying Enter key on password field.")
            try:
                password_locator = await self._first_visible_locator(
                    page,
                    [
                        "input[type='password']",
                        "input[placeholder*='Password']",
                        "input[name='password']",
                    ],
                )
                await password_locator.press("Enter")
                await asyncio.sleep(8)
            except Exception:
                pass

        await self._dismiss_popups(page)
        if await self._wait_for_authenticated_session(page, timeout_seconds=20):
            print("Login verified successfully.")
            return

        print("Automatic login could not be verified. Waiting up to 600 seconds for manual login/CAPTCHA completion on the current page...")
        if await self._wait_for_authenticated_session(page, timeout_seconds=600):
            print("Manual login detected.")
            return

        raise RuntimeError("Login did not complete. Please complete login/CAPTCHA manually and rerun.")

    async def _logout(self, page: Page) -> bool:
        try:
            await self._safe_goto(page, "https://www.naukri.com/mnjuser/homepage")
        except Exception:
            pass
        await asyncio.sleep(2)
        await self._dismiss_popups(page)

        for menu_selector in [
            "div.nI-gNb-drawer__bars",
            "div.nI-gNb-drawer__icon",
            "img[alt*='profile']",
            "a:has-text('My Naukri')",
            "div:has-text('My Naukri')",
        ]:
            try:
                menu = page.locator(menu_selector).first
                if await menu.is_visible(timeout=1200):
                    await menu.click()
                    await asyncio.sleep(1)
                    break
            except Exception:
                continue

        for logout_selector in [
            "a:has-text('Logout')",
            "a:has-text('Log out')",
            "a:has-text('Sign out')",
            "button:has-text('Logout')",
            "text=Logout",
        ]:
            try:
                logout = page.locator(logout_selector).first
                if await logout.is_visible(timeout=1500):
                    await logout.click()
                    await asyncio.sleep(4)
                    break
            except Exception:
                continue

        if await self._is_visible(page, "button:has-text('Login')", timeout=2000):
            print("Logout detected (Login button visible).")
            return True

        try:
            await self._safe_goto(page, "https://www.naukri.com/")
            await asyncio.sleep(2)
        except Exception:
            pass
        ok = await self._is_visible(page, "button:has-text('Login')", timeout=2000)
        if ok:
            print("Logout detected after homepage navigation.")
        return ok

    async def process_search(self, page: Page, title: str, experience: int, location: str) -> None:
        print(f"Searching {title} | {experience} | {location}")
        await self._safe_goto(page, "https://www.naukri.com/")
        await asyncio.sleep(3)
        await self._dismiss_popups(page)

        if not await self._has_authenticated_session(page):
            print("Login button still visible on homepage. Re-running login flow.")
            await self.ensure_logged_in(page)
            await self._safe_goto(page, "https://www.naukri.com/")
            await asyncio.sleep(3)
            await self._dismiss_popups(page)

        if not await self._has_authenticated_session(page):
            raise RuntimeError("Search aborted because Naukri is still not logged in.")

        try:
            await page.locator(".nI-gNb-sb__main").first.click()
            await asyncio.sleep(1)
        except Exception:
            pass

        await self._fill_first_visible(
            page,
            [
                "input[placeholder='Enter keyword / designation / companies']",
                "input[placeholder='Enter skills / designations / companies']",
                "input[placeholder*='skills / designations']",
                "input[placeholder*='designation / companies']",
            ],
            title,
        )
        print("Filled keyword.")
        await self._select_experience(page, experience)
        print(f"Selected experience: {experience}")
        location_input = await self._first_visible_locator(
            page,
            [
                "input[placeholder='Enter location']",
                "input[placeholder*='location']",
            ],
        )
        await location_input.fill(location)
        await asyncio.sleep(1)
        await location_input.press("ArrowDown")
        await location_input.press("Enter")
        print(f"Filled location: {location}")

        clicked_search = False
        for selector in [
            "button.nI-gNb-sb__icon-wrapper",
            "button.qsbSubmit",
            "button:has-text('Search')",
            "button[type='submit']",
            "text=Search",
        ]:
            try:
                locator = page.locator(selector).first
                if await locator.is_visible(timeout=2000):
                    await locator.click()
                    clicked_search = True
                    print(f"Clicked search using selector: {selector}")
                    await page.wait_for_load_state("domcontentloaded")
                    break
            except Exception:
                continue

        if not clicked_search:
            print("Search button selector did not resolve. Using Enter key fallback.")
            await location_input.press("Enter")
        await asyncio.sleep(5)
        await self._apply_salary_filter(page)
        await self._walk_results_pages(page, title, experience, location)

    async def _dismiss_popups(self, page: Page) -> None:
        for selector in [
            "button:has-text('Later')",
            "button:has-text('Skip')",
            "span.crossIcon",
            "button.close",
        ]:
            try:
                locator = page.locator(selector).first
                if await locator.is_visible(timeout=800):
                    await locator.click()
                    await asyncio.sleep(1)
            except Exception:
                continue

    async def _select_experience(self, page: Page, experience: int) -> None:
        locator = await self._first_visible_locator(
            page,
            [
                "#experienceDD",
                "input[placeholder='Select experience']",
                "input[placeholder*='experience']",
                "div[title='Select experience']",
                "span:has-text('Select experience')",
                "div:has(input[placeholder*='experience'])",
            ],
        )
        await locator.click()
        await asyncio.sleep(1)

        option_titles = [f"{experience} years", f"{experience} year"]
        for label in option_titles:
            option = page.locator(f"li[title='{label}']").first
            if await option.count():
                await option.click()
                await asyncio.sleep(1)
                return

    async def _apply_salary_filter(self, page: Page) -> None:
        band = self.config.search.salary_band
        selectors = [
            f"label:has-text('{band}')",
            f"span:has-text('{band}')",
            f"text='{band}'",
        ]
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if await locator.is_visible(timeout=3000):
                    await locator.scroll_into_view_if_needed()
                    await locator.click()
                    await asyncio.sleep(1)
                    break
            except Exception:
                continue

        for selector in ["button:has-text('Apply')", "button[type='submit']"]:
            try:
                locator = page.locator(selector).first
                if await locator.is_visible(timeout=2000):
                    await locator.click()
                    await asyncio.sleep(4)
                    return
            except Exception:
                continue

    async def _walk_results_pages(self, page: Page, title: str, experience: int, location: str) -> None:
        jobs_seen_for_search = 0
        for _ in range(self.config.search.max_pages):
            try:
                await page.wait_for_selector("div.srp-jobtuple-wrapper", timeout=10000)
            except Exception:
                pass
            cards = await page.locator("div.srp-jobtuple-wrapper").all()
            if not cards:
                print(f"[{self.site_name}] No job cards found on this page.")
                return

            for index in range(len(cards)):
                cards = await page.locator("div.srp-jobtuple-wrapper").all()
                if index >= len(cards):
                    break
                if len(self.jobs) >= self.config.search.max_jobs:
                    return
                if jobs_seen_for_search >= self.config.search.max_jobs_per_search:
                    return
                await self._inspect_job_card(page, index, title, experience, location)
                jobs_seen_for_search += 1

            next_button = page.locator("a[aria-label='Next'], a:has-text('Next')").first
            try:
                if await next_button.is_visible(timeout=1500):
                    await next_button.click()
                    await page.wait_for_load_state("domcontentloaded")
                    await asyncio.sleep(4)
                else:
                    return
            except Exception:
                return

    async def _inspect_job_card(self, page: Page, index: int, title: str, experience: int, location: str) -> None:
        cards = await page.locator("div.srp-jobtuple-wrapper").all()
        card = cards[index]
        results_url = page.url
        title_text = await self._safe_inner_text(card.locator("a.title").first)
        company = await self._safe_inner_text(card.locator("[class*='comp-name']").first)
        card_location = await self._safe_inner_text(card.locator("span.locWdth").first) or location
        job_exp = await self._safe_inner_text(card.locator("span.expwdth, [class*='exp'], li.experience").first) or "Not specified"
        salary = await self._safe_inner_text(card.locator("[class*='salary']").first) or "Not disclosed"
        posted = await self._safe_inner_text(card.locator("span.job-post-day").first)

        original_page = page
        popup_page: Optional[Page] = None
        popup_task = asyncio.create_task(original_page.context.wait_for_event("page"))
        await card.click()
        await asyncio.sleep(3)
        if popup_task.done():
            popup_page = popup_task.result()
            await popup_page.wait_for_load_state("domcontentloaded")
            detail_page = popup_page
        else:
            popup_task.cancel()
            detail_page = original_page

        try:
            try:
                await detail_page.wait_for_load_state("networkidle", timeout=20000)
            except Exception:
                pass
            await asyncio.sleep(2)
            job_url = detail_page.url
            apply_type = await self._detect_apply_type(detail_page)
            applied = False
            status = "captured"
            notes_parts: list[str] = []
            resume_updated = False

            if apply_type == "apply_on_company_site":
                status = "requires_manual_follow_up"
                notes_parts.append("Apply on company site detected")
            elif apply_type == "apply":
                applied, status, action_notes = await self._apply_to_job(detail_page)
                notes_parts.extend(action_notes)
            else:
                normalized_apply_type = await self._infer_apply_type_from_cta(detail_page)
                apply_type = normalized_apply_type
                if apply_type == "apply_on_company_site":
                    status = "requires_manual_follow_up"
                    notes_parts.append("Apply on company site detected")
                elif apply_type == "apply":
                    applied, status, action_notes = await self._apply_to_job(detail_page)
                    notes_parts.extend(action_notes)
                else:
                    status = "review_required"
                    notes_parts.append("Could not classify apply type from visible CTA")

            if self.profile_resume_refreshed:
                notes_parts.insert(0, "Profile resume updated after login")

            self.jobs.append(
                JobRecord(
                    title=title_text,
                    company=company,
                    location=card_location,
                    jobExperienceReq=job_exp,
                    salary=salary,
                    searchTitle=title,
                    searchExperience=experience,
                    searchLocation=location,
                    jobUrl=job_url,
                    applyType=apply_type,
                    applied=applied,
                    status=status,
                    notes=" | ".join(notes_parts) or "-",
                    resumeUpdated=self.profile_resume_refreshed,
                    postedDate=posted,
                    lastCheckedAt=datetime.now().isoformat(),
                )
            )
            write_jobs_snapshot(JOBS_JSON_PATH, [asdict(job) for job in self.jobs])
        finally:
            if popup_page:
                await popup_page.close()
            else:
                await self._safe_goto(page, results_url)
                await asyncio.sleep(3)

    async def _detect_apply_type(self, page: Page) -> str:
        for selector in [
            "button:has-text('Apply on company site')",
            "a:has-text('Apply on company site')",
        ]:
            try:
                locator = page.locator(selector).first
                if await locator.is_visible(timeout=1200):
                    return "apply_on_company_site"
            except Exception:
                continue

        for selector in [
            "button#apply-button",
            "button:has-text('Apply')",
            "a:has-text('Apply')",
            "button:has-text('Login to apply')",
            "button:has-text('Register to apply')",
        ]:
            try:
                locator = page.locator(selector).first
                if await locator.is_visible(timeout=1200):
                    text = (await locator.inner_text()).strip().lower()
                    if "company site" not in text:
                        return "apply"
            except Exception:
                continue
        return "none"

    async def _update_profile_resume_once(self, page: Page) -> bool:
        await self._safe_goto(page, "https://www.naukri.com/mnjuser/homepage")
        await asyncio.sleep(3)
        for selector in [
            "a:has-text('View & Update Profile')",
            "a:has-text('Update Profile')",
            "button:has-text('Update resume')",
            "a:has-text('Update resume')",
        ]:
            try:
                locator = page.locator(selector).first
                if await locator.is_visible(timeout=1000):
                    await locator.click()
                    await asyncio.sleep(3)
                    break
            except Exception:
                continue
        else:
            await self._safe_goto(page, "https://www.naukri.com/mnjuser/profile")
            await asyncio.sleep(3)

        uploaded = await self._upload_resume_if_possible(page)
        return uploaded


    async def _apply_to_job(self, page: Page) -> tuple[bool, str, list[str]]:
        notes: list[str] = []
        # Pre-check if already applied
        for selector in ["text=Already applied", "button:has-text('Applied')", "span:has-text('Applied')"]:
            try:
                if await self._is_visible(page, selector, timeout=1000):
                    return True, "already_applied", ["Job was already applied"]
            except Exception:
                continue

        clicked, button_text = await self._click_apply_cta(page)
        if not clicked:
            return False, "apply_failed", ["Apply button was expected but not clickable"]
        notes.append(f"Apply button clicked: {button_text}")
        await asyncio.sleep(3)

        for _ in range(8):
            question_notes = []
            question_notes.extend(await self._handle_chatbot_questions(page))
            question_notes.extend(await self._fill_screening_questions(page))
            for note in question_notes:
                if note not in notes:
                    notes.append(note)

            confirmed, confirmation_note = await self._wait_for_apply_confirmation(page, timeout_seconds=2)
            if confirmed:
                notes.append(confirmation_note)
                return True, "applied", notes

            advanced, action_note = await self._click_apply_flow_action(page)
            if advanced:
                notes.append(action_note)
                await asyncio.sleep(2)
                continue

            if not question_notes:
                break

        confirmed, confirmation_note = await self._wait_for_apply_confirmation(page)
        notes.append(confirmation_note)
        return True, "applied" if confirmed else "applied_unconfirmed", notes

    async def _click_apply_cta(self, page: Page) -> tuple[bool, str]:
        # Priority selectors for Naukri's specific 'Apply' buttons
        priority_selectors = [
            "button.apply-button",
            "button:has-text('Apply')",
            "button.nLnk",
            "button[class*='apply']",
            "a:has-text('Apply Now')",
            "button:has-text('Apply Now')",
            "button:has-text('Login to apply')",
            "button:has-text('Register to apply')",
            "button#apply-button",
            "a#apply-button"
        ]

        for selector in priority_selectors:
            try:
                element = page.locator(selector).first
                if await element.is_visible(timeout=1500) and await element.is_enabled():
                    text = (await element.inner_text()).strip()
                    if text and "company site" not in text.lower():
                        print(f"[Naukri] Found Apply button: {text}")
                        await element.scroll_into_view_if_needed()
                        await asyncio.sleep(1)
                        try:
                            await element.click(timeout=5000)
                        except Exception:
                            await element.click(force=True, timeout=5000)
                        return True, text
            except Exception:
                continue

        # Fallback to general scan
        candidate_selectors = ["button", "a", "div[role='button']"]
        for selector in candidate_selectors:
            try:
                elements = await page.locator(selector).all()
            except Exception:
                continue

            for element in elements[:50]:
                try:
                    if not await element.is_visible() or not await element.is_enabled():
                        continue
                    text = (await element.inner_text()).strip()
                    lowered = text.lower()
                    if not lowered or "company site" in lowered:
                        continue
                    if "apply" in lowered:
                        print(f"[Naukri] Found Apply button (general scan): {text}")
                        await element.scroll_into_view_if_needed()
                        await asyncio.sleep(1)
                        await element.click(force=True)
                        return True, text
                except Exception:
                    continue

        return False, ""

    async def _wait_for_apply_confirmation(self, page: Page, timeout_seconds: int = 12) -> tuple[bool, str]:
        success_selectors = [
            "text=You have applied successfully",
            "text=Applied successfully",
            "text=Application submitted",
            "text=Successfully applied",
            "text=You have successfully applied",
            "text=already applied",
            "text=Already applied",
            "button:has-text('Applied')",
            "span:has-text('Applied')",
            ".applied",
        ]

        for _ in range(timeout_seconds):
            for selector in success_selectors:
                try:
                    locator = page.locator(selector).first
                    if await locator.is_visible(timeout=500):
                        text = (await locator.inner_text()).strip()
                        if text:
                            print(f"\n[VALIDATION] Application confirmation detected: {text}\n")
                            return True, f"Application confirmation detected: {text}"
                        print("\n[VALIDATION] Application confirmation detected\n")
                        return True, "Application confirmation detected"
                except Exception:
                    continue

            try:
                html = (await page.content()).lower()
                for phrase in [
                    "you have applied successfully",
                    "applied successfully",
                    "application submitted",
                    "successfully applied",
                    "already applied",
                ]:
                    if phrase in html:
                        print(f"\n[VALIDATION] Application confirmation detected (from page HTML): {phrase}\n")
                        return True, f"Application confirmation detected: {phrase}"
            except Exception:
                pass

            await asyncio.sleep(1)

        return False, "Apply flow triggered but final confirmation was not detected"

    async def _fill_screening_questions(self, page: Page) -> list[str]:
        notes: list[str] = []
        containers = await page.locator(
            "div[class*='question'], div.question-wrapper, .chatbot-question, "
            "div.singleselect-radiobutton-container, div.multicheckboxes-container, "
            "div.form-field, div.field-wrapper"
        ).all()
        for container in containers:
            try:
                # Try to find the question text inside the container
                question_elem = await self._first_visible_locator(
                    container,
                    ["label", "p", "span", "div.question-text"],
                    timeout=500
                )
                if not question_elem:
                    continue
                question = await self._safe_inner_text(question_elem)
                if not question or len(question) < 5:
                    continue
                    
                filled, note = await self._fill_question_container(container, question)
                if filled and note:
                    notes.append(note)
            except Exception:
                continue

        # Fallback: scan visible labels in dialogs/forms when Naukri doesn't wrap them in a "question" div.
        notes.extend(await self._fill_from_visible_labels(page))
        notes.extend(await self._fill_button_choice_questions(page))
        return notes

    async def _handle_chatbot_questions(self, page: Page, max_turns: int = 15) -> list[str]:
        notes: list[str] = []
        for _ in range(max_turns):
            try:
                # Look for the latest bot message
                bot_msgs = await page.locator("div.botMsg, div[class*='botMsg'], div.chat-msg-bot").all()
                if not bot_msgs:
                    # Check if chatbot is even present
                    if not await self._is_visible(page, ".chatbot-container, .chat-window, .chatbot"):
                        return notes
                    await asyncio.sleep(2)
                    continue
                    
                latest = bot_msgs[-1]
                question = (await latest.inner_text()).strip()
                if not question or "..." in question: # Avoid typing while bot is 'thinking'
                    await asyncio.sleep(2)
                    continue

                # Get answer from Groq
                answer = self._heuristic_answer(question) or self.answerer.answer(question)
                
                # Find the input box
                input_box = await self._first_visible_locator(
                    page,
                    [
                        "div.textArea[contenteditable='true']",
                        "div[contenteditable='true']",
                        "textarea.chat-input",
                        "input.chat-input"
                    ],
                    timeout=3000
                )
                
                if not input_box:
                    return notes
                    
                await input_box.scroll_into_view_if_needed()
                await asyncio.sleep(0.5)
                await input_box.click()
                await input_box.fill("")
                await input_box.press_sequentially(answer, delay=30)
                await asyncio.sleep(0.5)
                
                # Try to find a 'Send' button first, then fallback to Enter
                send_btn = await self._first_visible_locator(
                    page,
                    ["button.send-btn", "button:has-text('Send')", ".chatbot-footer button"],
                    timeout=1000
                )
                if send_btn:
                    await send_btn.click()
                else:
                    await input_box.press("Enter")
                    
                notes.append(f"Answered chatbot: {question[:40]}... -> {answer}")
                await asyncio.sleep(3) # Wait for bot response
            except Exception as e:
                print(f"[Naukri] Chatbot turn failed: {e}")
                return notes
        return notes

    async def _fill_from_visible_labels(self, page: Page) -> list[str]:
        notes: list[str] = []

        scope = page
        dialog = page.locator("[role='dialog']:visible, div[class*='modal']:visible").first
        try:
            if await dialog.count():
                scope = dialog
        except Exception:
            scope = page

        labels = await scope.locator("label:visible").all()
        for label in labels[:40]:
            try:
                q = (await label.inner_text()).strip()
                if not q or len(q) < 3:
                    continue

                for_attr = await label.get_attribute("for")
                input_locator = None
                if for_attr:
                    input_locator = scope.locator(f"#{for_attr}").first
                if not input_locator or not await input_locator.count():
                    input_locator = label.locator("xpath=following::input[1]").first

                if await input_locator.count():
                    typ = (await input_locator.get_attribute("type") or "").lower()
                    if typ in {"radio", "checkbox", "file", "hidden"}:
                        continue
                    answer = self._heuristic_answer(q) or self.answerer.answer(q)
                    await input_locator.scroll_into_view_if_needed()
                    await asyncio.sleep(0.5)
                    await input_locator.fill("")
                    await input_locator.press_sequentially(answer, delay=30)
                    notes.append(f"Answered labeled input: {q} -> {answer}")
                    await asyncio.sleep(0.5)
            except Exception:
                continue

        return notes

    async def _fill_button_choice_questions(self, page: Page) -> list[str]:
        notes: list[str] = []

        scope = page
        dialog = page.locator("[role='dialog']:visible, div[class*='modal']:visible").first
        try:
            if await dialog.count():
                scope = dialog
        except Exception:
            scope = page

        containers = await scope.locator(
            "div.singleselect-radiobutton-container:visible, "
            "div.multicheckboxes-container:visible, "
            "div[role='radiogroup']:visible, "
            "div[role='group']:visible"
        ).all()

        for container in containers[:20]:
            try:
                question = await self._safe_inner_text(container.locator("label, p, span, h3").first)
                if not question:
                    continue

                candidates = await container.locator(
                    "label:visible, button:visible, [role='radio']:visible, [role='option']:visible"
                ).all()
                options: list[str] = []
                for candidate in candidates[:20]:
                    text = (await candidate.inner_text()).strip()
                    if text and len(text) <= 80 and text.lower() not in {"next", "submit", "proceed", "continue"}:
                        options.append(text)
                options = list(dict.fromkeys(options))
                if len(options) < 2:
                    continue

                chosen = self._choose_with_heuristics(question, options) or self.answerer.choose_option(question, options)
                if not chosen:
                    continue

                if await self._click_text_option(container, chosen):
                    notes.append(f"Selected visual option: {question} -> {chosen}")
            except Exception:
                continue

        return notes

    async def _fill_question_container(self, container, question: str) -> tuple[bool, str]:
        text_input = container.locator("input[type='text'], input[type='number'], textarea").first
        if await text_input.count():
            answer = self._heuristic_answer(question) or self.answerer.answer(question)
            await text_input.scroll_into_view_if_needed()
            await asyncio.sleep(0.5)
            await text_input.fill("")
            await text_input.press_sequentially(answer, delay=30)
            await asyncio.sleep(0.5)
            return True, f"Answered text question: {question} -> {answer}"

        select = container.locator("select").first
        if await select.count():
            option_elements = await select.locator("option").all()
            options = []
            for option in option_elements:
                text = (await option.inner_text()).strip()
                if text and "select" not in text.lower():
                    options.append(text)
            if options:
                chosen = self.answerer.choose_option(question, options)
                await select.select_option(label=chosen)
                return True, f"Selected option: {question} -> {chosen}"

        radio_buttons = await container.locator("input[type='radio']").all()
        if radio_buttons:
            options = await self._extract_input_options(container, radio_buttons)
            chosen = self._choose_with_heuristics(question, options) or self.answerer.choose_option(question, options)
            if chosen:
                await self._check_matching_option(container, radio_buttons, chosen)
                return True, f"Selected radio option: {question} -> {chosen}"

        checkboxes = await container.locator("input[type='checkbox']").all()
        if checkboxes:
            options = await self._extract_input_options(container, checkboxes)
            chosen = self._choose_with_heuristics(question, options) or self.answerer.choose_option(question, options)
            if chosen:
                await self._check_matching_option(container, checkboxes, chosen)
                return True, f"Selected checkbox option: {question} -> {chosen}"

        return False, ""

    async def _click_apply_flow_action(self, page: Page) -> tuple[bool, str]:
        action_selectors = [
            "button:has-text('Submit')",
            "button:has-text('Send Application')",
            "button:has-text('Proceed')",
            "button:has-text('Continue')",
            "button:has-text('Next')",
            "button:has-text('Review')",
            "button:has-text('Save')",
            "button:has-text('Save & Next')",
            "button:has-text('Confirm')",
            "button:has-text('Done')",
            "button:has-text('Apply')",
            "button:has-text('Send')",
            "button[type='submit']",
            "button.btn-primary",
            "button[class*='primary']",
            ".chatbot-footer button",
            "button[class*='send']",
        ]

        for selector in action_selectors:
            try:
                locator = page.locator(selector).first
                if await locator.is_visible(timeout=1000) and await locator.is_enabled():
                    button_text = (await locator.inner_text()).strip() or selector
                    await locator.click(force=True)
                    return True, f"Apply flow action clicked: {button_text}"
            except Exception:
                continue

        for selector in ["button", "a", "[role='button']"]:
            try:
                elements = await page.locator(selector).all()
            except Exception:
                continue

            for element in elements[:60]:
                try:
                    if not await element.is_visible() or not await element.is_enabled():
                        continue
                    text = (await element.inner_text()).strip()
                    lowered = text.lower()
                    if lowered in {"submit", "send application", "proceed", "continue", "next", "review", "done", "save", "save & next", "confirm", "send", "apply"}:
                        await element.click(force=True)
                        return True, f"Apply flow action clicked: {text}"
                except Exception:
                    continue

        return False, ""

    async def _extract_input_options(self, container, inputs) -> list[str]:
        options: list[str] = []
        labels = await container.locator("label").all()
        for label in labels:
            text = (await label.inner_text()).strip()
            if text:
                options.append(text)
        if options:
            return options

        for input_locator in inputs:
            try:
                input_id = await input_locator.get_attribute("id")
                if input_id:
                    label = container.locator(f"label[for='{input_id}']").first
                    if await label.count():
                        text = (await label.inner_text()).strip()
                        if text:
                            options.append(text)
                            continue
                value = await input_locator.get_attribute("value")
                if value:
                    options.append(value.strip())
            except Exception:
                continue
        return options

    async def _check_matching_option(self, container, inputs, chosen: str) -> None:
        chosen_lower = chosen.lower()
        for input_locator in inputs:
            try:
                input_id = await input_locator.get_attribute("id")
                candidate_text = ""
                label_locator = None
                
                # 1. Try label by ID
                if input_id:
                    label_locator = container.locator(f"label[for='{input_id}']").first
                    if await label_locator.count():
                        candidate_text = (await label_locator.inner_text()).strip()
                
                # 2. Try ancestor label
                if not candidate_text:
                    parent_label = input_locator.locator("xpath=ancestor::label").first
                    if await parent_label.count():
                        candidate_text = (await parent_label.inner_text()).strip()
                        label_locator = parent_label
                        
                # 3. Try following sibling (often a span containing text)
                if not candidate_text:
                    next_sibling = input_locator.locator("xpath=following-sibling::*[1]").first
                    if await next_sibling.count():
                        candidate_text = (await next_sibling.inner_text()).strip()
                        label_locator = next_sibling
                        
                # 4. Try parent div
                if not candidate_text:
                    parent = input_locator.locator("xpath=..").first
                    if await parent.count():
                        candidate_text = (await parent.inner_text()).strip()
                        label_locator = parent
                        
                # 5. Value fallback
                if not candidate_text:
                    value = await input_locator.get_attribute("value")
                    candidate_text = (value or "").strip()
                    
                if candidate_text and (
                    candidate_text.lower() == chosen_lower
                    or chosen_lower in candidate_text.lower()
                    or candidate_text.lower() in chosen_lower
                ):
                    await input_locator.scroll_into_view_if_needed()
                    await asyncio.sleep(0.5)
                    
                    if label_locator and await label_locator.count():
                        await label_locator.click(force=True)
                    else:
                        await input_locator.click(force=True)
                    
                    try:
                        await input_locator.check(force=True)
                    except Exception:
                        pass
                        
                    await asyncio.sleep(0.5)
                    return
            except Exception as e:
                print(f"Error checking option: {e}")
                continue
                
        await inputs[0].scroll_into_view_if_needed()
        await asyncio.sleep(0.5)
        # fallback click the first parent or input
        try:
            parent = inputs[0].locator("xpath=..").first
            if await parent.count():
                await parent.click(force=True)
            else:
                await inputs[0].click(force=True)
        except Exception:
             pass
        try:
            await inputs[0].check(force=True)
        except Exception:
            pass
        await asyncio.sleep(0.5)

    async def _click_text_option(self, container, chosen: str) -> bool:
        chosen_lower = chosen.lower()
        candidates = await container.locator(
            "label:visible, button:visible, [role='radio']:visible, [role='option']:visible"
        ).all()

        for candidate in candidates:
            try:
                text = (await candidate.inner_text()).strip()
                if not text:
                    continue
                lowered = text.lower()
                if lowered == chosen_lower or chosen_lower in lowered or lowered in chosen_lower:
                    await candidate.scroll_into_view_if_needed()
                    await asyncio.sleep(0.5)
                    await candidate.click(force=True)
                    await asyncio.sleep(0.5)
                    return True
            except Exception:
                continue

        return False

    def _choose_with_heuristics(self, question: str, options: list[str]) -> str:
        return ""

    def _heuristic_answer(self, question: str) -> str:
        return ""


    async def _has_authenticated_session(self, page: Page) -> bool:
        if await self._is_visible(page, "button:has-text('Login')", timeout=500):
            return False
        if await self._is_visible(page, "button:has-text('Register')", timeout=500):
            return False
        if await self._is_visible(page, "button:has-text('Login to apply')", timeout=500):
            return False
        if await self._is_visible(page, "button:has-text('Register to apply')", timeout=500):
            return False
        # Check for presence of login form elements
        if await self._is_visible(page, "input[type='email']", timeout=500):
            return False
        if await self._is_visible(page, "input[type='password']", timeout=500):
            return False
        if await self._is_visible(page, "input[placeholder*='Email']", timeout=500):
            return False
        if await self._is_visible(page, "input[placeholder*='Password']", timeout=500):
            return False
        # Check for presence of login form elements
        if await self._is_visible(page, "input[type='email']", timeout=500):
            return False
        if await self._is_visible(page, "input[type='password']", timeout=500):
            return False
        if await self._is_visible(page, "input[placeholder*='Email']", timeout=500):
            return False
        if await self._is_visible(page, "input[placeholder*='Password']", timeout=500):
            return False

        positive_selectors = [
            "a:has-text('View & Update Profile')",
            "a:has-text('My Naukri')",
            "[href*='mnjuser/profile']",
            "[href*='mnjuser/homepage']",
            "div.nI-gNb-drawer__bars",
            "img[alt*='profile']",
        ]
        for selector in positive_selectors:
            if await self._is_visible(page, selector, timeout=500):
                return True

        url = page.url.lower()
        html = (await page.content()).lower()
        if "mnjuser" in url and "login to apply" not in html and ">login<" not in html:
            return True
        return False




    async def _infer_apply_type_from_cta(self, page: Page) -> str:
        for selector in ["button", "a"]:
            elements = await page.locator(selector).all()
            for element in elements[:20]:
                try:
                    text = (await element.inner_text()).strip().lower()
                except Exception:
                    continue
                if not text:
                    continue
                if "apply on company site" in text:
                    return "apply_on_company_site"
                if "apply" in text:
                    return "apply"
        return "none"


    async def _wait_for_authenticated_session(self, page: Page, timeout_seconds: int) -> bool:
        for _ in range(timeout_seconds):
            try:
                if await self._has_authenticated_session(page):
                    return True
            except Exception:
                pass
            await asyncio.sleep(1)
        return False
