"""Scheduled scraper for top crypto and security papers from arXiv."""

import logging
from dataclasses import dataclass
from typing import Any, Final

import feedparser
import requests
from fastapi import APIRouter

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

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the scheduler and its state."""
        super().__init__(*args, **kwargs)

        # Store the latest papers in memory
        self.latest_papers: list[ArxivPaper] = []

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
        self.latest_papers = papers
        for paper in papers:
            LOGGER.debug("Paper: %s (ID: %s)", paper.title, paper.arxiv_id)


@cron_job(name="arxiv_papers")
def _register() -> CronJobEntry:
    """Register the arXiv papers scraper job.

    Returns:
        CronJobEntry with the configured scheduler and status.
    """
    status = ServiceStatus(name="arxiv_scheduler", enabled=True)
    scheduler = ArxivScheduler(interval_seconds=ONE_DAY_SECONDS, status=status)

    router = APIRouter()

    @router.get("/papers")
    def get_papers(limit: int = 25):  # noqa: ANN202
        """Return the latest crypto/security papers from arXiv.

        Args:
            limit: Maximum number of papers to return (default 25).

        Returns:
            A dictionary with paper count and list of paper objects.
        """
        papers = scheduler.latest_papers[:limit]
        return {
            "limit": limit,
            "count": len(papers),
            "papers": [
                {
                    "title": p.title,
                    "authors": p.authors,
                    "published": p.published,
                    "arxiv_id": p.arxiv_id,
                    "summary": p.summary,
                    "link": p.link,
                    "pdf_link": p.pdf_link,
                }
                for p in papers
            ],
        }

    return CronJobEntry(name="arxiv_papers", scheduler=scheduler, status=status, router=router)


if __name__ == "__main__":
    # For standalone testing
    status = ServiceStatus(name="arxiv_scheduler", enabled=True)
    scheduler = ArxivScheduler(interval_seconds=ONE_DAY_SECONDS, status=status)
    scheduler._run_job()
