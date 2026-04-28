"""Scrape the current month and next month from an Outlook published HTML calendar.

Install:
    playwright install chromium

Run:
    python scraper.py
"""

import datetime
import json
import re
from pathlib import Path
from typing import Final

from playwright.sync_api import Page, sync_playwright

from reachy_assistant.services.calendars import scraper
from reachy_assistant.services.calendars.event import CalendarEvent

CALENDAR_URL: Final[str] = (
    "https://outlook.cloud.microsoft/calendar/published/ba5da3d6d9f74a1eb6e3955cd10c2186@ece.gatech.edu/8aa6352871ff4e648ada00d1a273797312192055347853153433/calendar.html"
)


class Scraper(scraper.Scraper):
    """Scraper for the Hive Outlook calendar."""

    def clean(self, text: str | None) -> str:
        """Clean text by collapsing whitespace and stripping.

        Args:
            text: The input text to clean.

        Returns:
            Cleaned text with collapsed whitespace and no leading/trailing spaces.
        """
        if not text:
            return ""
        return re.sub(r"\s+", " ", text).strip()

    def get_current_month(self, page: Page) -> str:
        """Get the current month displayed on the calendar page.
        Tries multiple selectors to find a label that contains a month and year.

        Args:
            page: Playwright page object.

        Returns:
            The current month as a string, or "Unknown Month" if not found.
        """
        # First try the timestrip button which shows "April 2026"
        candidates = [
            "button[data-telemetry-id='TimestripButton']",
            "span.zytMo",
            "button[aria-label*='Jump to a specific date']",
            "button[title*='2026']",
            "button[aria-label*='Month']",
            "[aria-label*='Month']",
            "[class*='month-title']",
            "[class*='monthTitle']",
            "h1",
            "h2",
            "header",
            "[class*='month']",
            "[class*='title']",
        ]
        for sel in candidates:
            try:
                locator = page.locator(sel)
                count = locator.count()
                if count > 0:
                    for i in range(min(count, 8)):
                        text = self.clean(locator.nth(i).inner_text())
                        if text and re.search(
                            # Look for patterns like "April 2026"
                            r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}",
                            text,
                        ):
                            return text
            except Exception:  # noqa: S112
                continue
        return "Unknown Month"

    def parse_event_text(self, text: str) -> tuple[str, str | None]:
        """Parse event text to extract title, time, and location.

        Args:
            text: Raw text from the event element.

        Returns:
            Tuple of (title, time_text), where time_text may be None if not found.
        """
        parts = [self.clean(p) for p in re.split(r"[\n\r]+", text) if self.clean(p)]
        title = parts[0] if parts else ""

        time_text = None

        time_re = re.compile(r"\b(\d{1,2}:\d{2}\s*[APMapm]{2}|\d{1,2}\s*[APMapm]{2}|All day|Noon|Midnight)\b")
        for part in parts:
            if time_text is None and time_re.search(part):
                time_text = part

        return title, time_text

    def extract_modal_datetime(self, page: Page) -> str | None:
        """Extract datetime from the event details modal.

        Args:
            page: Playwright page object.

        Returns:
            The datetime text extracted from the modal, or None if not found.
        """
        modal_selectors = [
            "[role='dialog']",
            ".ms-Modal",
            "[class*='modal']",
            "[class*='popup']",
        ]

        for sel in modal_selectors:
            modal = page.locator(sel).first
            if modal.is_visible():
                try:
                    text = self.clean(modal.inner_text())
                    # Look for pattern like "Wed 4/15/2026 6:30 PM - 8:30 PM"
                    date_match = re.search(
                        r"(\w+\s+\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}\s*[APMapm]{2}(?:\s*-\s*\d{1,2}:\d{2}\s*[APMapm]{2})?)", text
                    )
                    if date_match:
                        return date_match.group(1)
                except Exception:  # noqa: BLE001, S110
                    pass
        return None

    def scrape_visible_month(self, page: Page) -> set[CalendarEvent]:
        """Scrape events from the currently visible month on the calendar page.

        Args:
            page: Playwright page object.

        Returns:
            Set of CalendarEvent objects extracted from the visible month.
        """
        month_label = self.get_current_month(page)
        events: set[CalendarEvent] = set()

        # Find clickable event elements - try broad selectors first
        selectors = [
            "[role='button']",
            "[role='link']",
            "[data-eventid]",
            "[class*='event']",
            "div[aria-label]",
        ]

        seen_texts = set()

        for sel in selectors:
            try:
                locator = page.locator(sel)
                count = min(locator.count(), 300)
                print(f"  Selector '{sel}' found {count} elements")

                for i in range(count):
                    try:
                        element = locator.nth(i)
                        text = self.clean(element.inner_text())
                        aria_label = element.get_attribute("aria-label") or ""

                        combined_text = f"{text} {aria_label}".strip()
                        if not combined_text or len(combined_text) < 2:
                            continue

                        # Skip navigation elements
                        if any(skip in combined_text.lower() for skip in ["next", "previous", "today", "month", "week"]):
                            continue

                        if combined_text in seen_texts:
                            continue
                        seen_texts.add(combined_text)

                        title, _ = self.parse_event_text(combined_text)
                        if not title or len(title) < 2:
                            continue

                        print(f"    Clicking event: {title}")

                        # Click the event to open modal
                        element.click()
                        page.wait_for_timeout(800)

                        # Extract datetime from modal
                        full_datetime = self.extract_modal_datetime(page)
                        time_text = None

                        if full_datetime:
                            print(f"      Found datetime: {full_datetime}")
                            # Parse "Wed 4/15/2026 6:30 PM - 8:30 PM"
                            time_match = re.search(r"(\d{1,2}:\d{2}\s*[APMapm]{2}(?:\s*-\s*\d{1,2}:\d{2}\s*[APMapm]{2})?)", full_datetime)
                            if time_match:
                                time_text = time_match.group(1)

                        # Close modal
                        close_button = page.locator("[aria-label='Close']").first
                        if close_button.is_visible():
                            close_button.click()
                            page.wait_for_timeout(300)
                        else:
                            page.keyboard.press("Escape")
                            page.wait_for_timeout(300)

                        # Extract year from month_label, handling unicode chars
                        year_match = re.search(r"\d{4}", month_label)
                        year = int(year_match.group(0)) if year_match else 2026

                        events.add(
                            CalendarEvent(
                                id=f"{month_label}_{title}_{time_text}",
                                date=full_datetime or combined_text,
                                semester="Unknown",
                                year=year,
                                category="Hive",
                                event=title,
                                link=None,
                                start_date=None,
                                end_date=None,
                            )
                        )
                    except Exception as e:  # noqa: BLE001
                        print(f"      Error processing element: {e}")
                        continue
            except Exception:  # noqa: BLE001, S112
                continue

        return events

    def click_next_month(self, page: Page) -> None:
        """Click the "Next Month" button on the calendar page.

        Args:
            page: Playwright page object.
        """
        candidates = [
            "button[aria-label*='Next']",
            "button[title*='Next']",
            "[aria-label*='next month']",
            "[aria-label*='Next month']",
            "button:has-text('Next')",
        ]

        for sel in candidates:
            locator = page.locator(sel)
            if locator.count() > 0:
                locator.first.click()
                page.wait_for_timeout(1500)
                return

        # Fallback: keyboard navigation sometimes works
        page.keyboard.press("PageDown")
        page.wait_for_timeout(1500)

    def scrape_calendar(self) -> set[CalendarEvent]:
        """Scrape the calendar and return a set of CalendarEvent.

        Returns:
            Set of CalendarEvent objects.

        Raises:
            Exception: on scraping failure.
        """
        # The main scraping logic is in the standalone function below
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            try:
                print("Loading calendar URL...")
                page.goto(CALENDAR_URL, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(1000)

                current_month_label = self.get_current_month(page)
                print(f"Current month: {current_month_label}")

                current_month_events = self.scrape_visible_month(page)
                print(f"Found {len(current_month_events)} events in current month")

                self.click_next_month(page)
                next_month_label = self.get_current_month(page)
                print(f"Next month: {next_month_label}")

                next_month_events = self.scrape_visible_month(page)
                print(f"Found {len(next_month_events)} events in next month")
            except Exception as e:  # pylint: disable=broad-exception-caught
                print(f"Error during scraping: {e}")
                current_month_events = set()
                current_month_label = "Unknown"
                next_month_events = set()
                next_month_label = "Unknown"
            finally:
                browser.close()

            data = {
                "scraped_at": datetime.datetime.now(datetime.UTC).isoformat(),
                "source": CALENDAR_URL,
                "months": [current_month_label, next_month_label],
                "events": [e.model_dump(mode="json") for e in current_month_events.union(next_month_events)],
            }

            with Path("hive_events.json").open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            return current_month_events


if __name__ == "__main__":
    Scraper().scrape_calendar()
