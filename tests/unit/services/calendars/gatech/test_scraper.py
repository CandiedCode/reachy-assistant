"""Unit tests for GaTech academic calendar scraper."""

import pytest

from reachy_assistant.services.calendars.gatech.scraper import RecordExtractionError, Scraper


@pytest.fixture
def scraper() -> Scraper:
    """Create a Scraper instance for testing.

    Returns:
        Scraper: A new Scraper instance.
    """
    return Scraper()


@pytest.fixture
def scraper_with_exclusions() -> Scraper:
    """Create a Scraper with category exclusions.

    Returns:
        Scraper: A Scraper with excluded categories.
    """
    return Scraper(excluded_categories=["Holiday", "Registration"])


class TestRecordExtraction:
    """Test _extract_records method."""

    @pytest.mark.parametrize(
        "input_data",
        [
            {"data": [{"id": "1", "event": "Test"}]},
            {"data": []},
            {"data": [{"id": "1"}, {"id": "2"}]},
        ],
    )
    def test_extract_records_from_dict_with_data_key(self, scraper: Scraper, input_data: dict) -> None:
        """Test extracting records from dict with 'data' key.

        Args:
            scraper: Scraper fixture instance.
            input_data: Input dictionary with 'data' key.
        """
        result = scraper._extract_records(input_data)
        assert result == input_data["data"]
        assert isinstance(result, list)

    @pytest.mark.parametrize(
        "input_list",
        [
            [{"id": "1"}],
            [{"id": "1"}, {"id": "2"}],
            [],
        ],
    )
    def test_extract_records_from_list(self, scraper: Scraper, input_list: list) -> None:
        """Test extracting records when input is already a list.

        Args:
            scraper: Scraper fixture instance.
            input_list: Input list of records.
        """
        result = scraper._extract_records(input_list)
        assert result == input_list

    def test_extract_records_raises_on_invalid_data(self, scraper: Scraper) -> None:
        """Test extraction fails with invalid data type.

        Args:
            scraper: Scraper fixture instance.
        """
        with pytest.raises(RecordExtractionError):
            scraper._extract_records("invalid")

    def test_extract_records_raises_on_dict_without_data_key(self, scraper: Scraper) -> None:
        """Test extraction fails when dict lacks 'data' key.

        Args:
            scraper: Scraper fixture instance.
        """
        with pytest.raises(KeyError):
            scraper._extract_records({"result": []})


class TestRecordParsing:
    """Test _parse_calendar_records method."""

    def test_parse_records_with_excluded_categories(self, scraper_with_exclusions: Scraper) -> None:
        """Test parsing filters out excluded categories.

        Args:
            scraper_with_exclusions: Scraper with exclusions.
        """
        records = [
            {
                "id": "1",
                "date": "January 1",
                "semester": "5F",
                "year": 2026,
                "category": "Holiday",
                "event": "New Year",
                "link": None,
            },
            {
                "id": "2",
                "date": "January 15",
                "semester": "5F",
                "year": 2026,
                "category": "Classes",
                "event": "Classes Begin",
                "link": None,
            },
        ]
        result = scraper_with_exclusions._parse_calendar_records(records, scraper_with_exclusions.excluded_categories)
        assert len(result) == 1
        event = result.pop()
        assert event.category == "Classes"

    @pytest.mark.parametrize(
        "category",
        ["Holiday", "Registration", "Exam", "Graduation"],
    )
    def test_parse_records_filters_various_categories(self, scraper: Scraper, category: str) -> None:
        """Test parsing filters various excluded categories.

        Args:
            scraper: Scraper fixture instance.
            category: Category to exclude.
        """
        records = [
            {
                "id": "1",
                "date": "January 1",
                "semester": "5F",
                "year": 2026,
                "category": category,
                "event": "Test Event",
                "link": None,
            },
        ]
        excluded = [category]
        result = scraper._parse_calendar_records(records, excluded)
        assert len(result) == 0

    def test_parse_records_handles_invalid_records(self, scraper: Scraper) -> None:
        """Test parsing handles invalid calendar records gracefully.

        Args:
            scraper: Scraper fixture instance.
        """
        records = [
            {"id": "1"},  # Missing required fields
            {"event": "Test"},  # Missing id
        ]
        result = scraper._parse_calendar_records(records, None)
        # Invalid records are skipped, no exception raised
        assert isinstance(result, set)


class TestRecordExtractionError:
    """Test RecordExtractionError exception."""

    def test_record_extraction_error_message(self) -> None:
        """Verify RecordExtractionError has correct message."""
        error = RecordExtractionError()
        assert str(error) == "Could not find record list in API response."

    def test_record_extraction_error_is_value_error(self) -> None:
        """Verify RecordExtractionError is a ValueError."""
        error = RecordExtractionError()
        assert isinstance(error, ValueError)
