"""Scheduled scraper for top crypto and security papers from arXiv."""

import logging
from dataclasses import dataclass
from typing import Final

import feedparser
import requests

from reachy_assistant.services.registry import CronJobEntry, cron_job
from reachy_assistant.services.scheduler import BaseScheduler
from reachy_assistant.services.status import ServiceStatus

LOGGER = logging.getLogger(__name__)

ONE_DAY_SECONDS: Final[int] = 24 * 60 * 60
ARXIV_API_URL: Final[str] = (
    "https://export.arxiv.org/api/query?search_query=(cat:cs.CR+OR+cat:cs.CY)&sortBy=submittedDate&sortOrder=descending&max_results=20"
)
REQUEST_TIMEOUT_SECONDS: Final[int] = 30


@dataclass
class ArxivPaper:
    """Represents a paper from arXiv."""

    title: str
    summary: str
    authors: list[str]
    published: str
    arxiv_id: str
    link: str
    pdf_link: str | None = None
    comment: str | None = None


class ArxivScheduler(BaseScheduler):
    """Runs the arXiv paper scraper on a daily schedule."""

    def _run_job(self) -> None:
        """Fetch the latest crypto and security papers from arXiv."""
        self._status.mark_started()
        try:
            response = requests.get(ARXIV_API_URL, timeout=REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            papers = self._parse_arxiv_feed(response.text)
            LOGGER.info("Successfully fetched %d crypto/security papers from arXiv", len(papers))
            self._process_papers(papers)
            self._status.mark_success()
        except requests.RequestException as e:
            self._status.mark_error(str(e))
            LOGGER.exception("Failed to fetch arXiv papers")

    def _parse_arxiv_feed(self, feed_xml: str) -> list[ArxivPaper]:
        """Parse arXiv Atom feed into ArxivPaper objects.

        Args:
            feed_xml: Raw XML response from arXiv API.

        Returns:
            List of parsed ArxivPaper objects.
        """
        feed: feedparser.FeedParserDict = feedparser.parse(feed_xml)
        papers = []

        for entry in feed.entries:
            authors = [str(author.name) for author in (entry.get("authors") or [])]
            pdf_link = None
            for link in entry.get("links") or []:
                if link.get("title") == "pdf":
                    pdf_link = str(link.get("href"))
                    break
            paper = ArxivPaper(
                title=str(entry.title),
                summary=str(entry.summary),
                authors=authors,
                published=str(entry.published),
                arxiv_id=str(entry.id).rsplit("/abs/", maxsplit=1)[-1],
                link=str(entry.link),
                pdf_link=pdf_link,
                comment=str(entry.get("arxiv_comment")) if entry.get("arxiv_comment") is not None else None,
            )
            papers.append(paper)

        return papers

    def _process_papers(self, papers: list[ArxivPaper]) -> None:
        """Process fetched papers.

        Args:
            papers: List of ArxivPaper objects to process.
        """
        for paper in papers:
            LOGGER.info("Paper: %s (ID: %s)", paper.title, paper.arxiv_id)


@cron_job(name="arxiv_papers")
def _register() -> CronJobEntry:
    """Register the arXiv papers scraper job.

    Returns:
        CronJobEntry with the configured scheduler and status.
    """
    status = ServiceStatus(name="arxiv_scheduler", enabled=True)
    scheduler = ArxivScheduler(interval_seconds=ONE_DAY_SECONDS, status=status)
    return CronJobEntry(name="arxiv_papers", scheduler=scheduler, status=status)


if __name__ == "__main__":
    # For standalone testing
    status = ServiceStatus(name="arxiv_scheduler", enabled=True)
    scheduler = ArxivScheduler(interval_seconds=ONE_DAY_SECONDS, status=status)
    scheduler._run_job()
