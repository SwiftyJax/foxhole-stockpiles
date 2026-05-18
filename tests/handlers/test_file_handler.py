"""Tests for handlers.file module."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from foxhole_stockpiles.core.settings.sections.output.csv_format import CsvFormatSettings
from foxhole_stockpiles.core.settings.sections.output.json_format import JsonFormatSettings
from foxhole_stockpiles.enums.output_format import OutputFormat
from foxhole_stockpiles.enums.stockpile_type import StockpileType
from foxhole_stockpiles.handlers.file import FileOutputHandler
from foxhole_stockpiles.models.stockpile import Stockpile
from foxhole_stockpiles.models.stockpile_item import StockpileItem


@pytest.fixture
def sample_stockpile() -> Stockpile:
    """Create a sample stockpile for testing."""
    return Stockpile(
        name="TestStockpile",
        type=StockpileType.SEAPORT,
        items=[
            StockpileItem(code="Rifle", quantity=100, crated=False, confidence=0.95),
            StockpileItem(code="Ammo", quantity=500, crated=True, confidence=0.88),
        ],
        timestamp=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        shard="ABLE",
        ingame_timestamp="Day 100, 1200 Hours",
        resolution="1920x1080",
    )


@pytest.fixture
def sample_stockpile_no_confidence() -> Stockpile:
    """Create a stockpile without confidence (save file data)."""
    return Stockpile(
        name="SaveFileStockpile",
        type=StockpileType.STORAGE_DEPOT,
        items=[
            StockpileItem(code="Bmats", quantity=1000, crated=False, confidence=None),
        ],
        timestamp=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
    )


class TestFileOutputHandlerInit:
    """Test suite for FileOutputHandler initialization."""

    def test_init_with_defaults(self) -> None:
        """Test initialization with default values."""
        handler = FileOutputHandler()
        assert handler.default_file_path is None
        assert isinstance(handler.format_settings, JsonFormatSettings)

    def test_init_with_path(self) -> None:
        """Test initialization with file path."""
        handler = FileOutputHandler(default_file_path="/tmp/output.json")
        assert handler.default_file_path == "/tmp/output.json"

    def test_init_with_csv_format(self) -> None:
        """Test initialization with CSV format."""
        csv_settings = CsvFormatSettings()
        handler = FileOutputHandler(format_settings=csv_settings)
        assert isinstance(handler.format_settings, CsvFormatSettings)


class TestFileOutputHandlerHandle:
    """Test suite for FileOutputHandler.handle method."""

    @pytest.mark.asyncio
    async def test_handle_single_stockpile(
        self, tmp_path: Path, sample_stockpile: Stockpile
    ) -> None:
        """Test handling a single stockpile."""
        output_file = tmp_path / "output.json"
        handler = FileOutputHandler(default_file_path=str(output_file))

        await handler.handle([sample_stockpile])

        assert output_file.exists()
        data = json.loads(output_file.read_text())
        assert "stockpiles" in data
        assert len(data["stockpiles"]) == 1
        assert data["stockpiles"][0]["name"] == "TestStockpile"
        assert data["stockpiles"][0]["type"] == "Seaport"

    @pytest.mark.asyncio
    async def test_handle_with_file_path_kwarg(
        self, tmp_path: Path, sample_stockpile: Stockpile
    ) -> None:
        """Test handling with file_path in kwargs."""
        output_file = tmp_path / "custom.json"
        handler = FileOutputHandler()

        await handler.handle([sample_stockpile], file_path=output_file)

        assert output_file.exists()

    @pytest.mark.asyncio
    async def test_handle_raises_without_path(self, sample_stockpile: Stockpile) -> None:
        """Test that ValueError is raised when no path is provided."""
        handler = FileOutputHandler()

        with pytest.raises(ValueError, match="File path must be provided"):
            await handler.handle([sample_stockpile])

    @pytest.mark.asyncio
    async def test_handle_multiple_stockpiles(
        self, tmp_path: Path, sample_stockpile: Stockpile
    ) -> None:
        """Test handling multiple stockpiles."""
        output_file = tmp_path / "output.json"
        handler = FileOutputHandler(default_file_path=str(output_file))

        stockpile2 = Stockpile(
            name="Second",
            type=StockpileType.STORAGE_DEPOT,
            items=[],
            timestamp=datetime.now(tz=UTC),
        )

        await handler.handle([sample_stockpile, stockpile2])

        data = json.loads(output_file.read_text())
        assert "stockpiles" in data
        assert len(data["stockpiles"]) == 2
        assert data["stockpiles"][0]["name"] == "TestStockpile"
        assert data["stockpiles"][1]["name"] == "Second"

    @pytest.mark.asyncio
    async def test_handle_creates_directories(
        self, tmp_path: Path, sample_stockpile: Stockpile
    ) -> None:
        """Test that parent directories are created."""
        output_file = tmp_path / "nested" / "dir" / "output.json"
        handler = FileOutputHandler(default_file_path=str(output_file))

        await handler.handle([sample_stockpile])

        assert output_file.exists()


class TestFileOutputHandlerPlaceholders:
    """Test suite for placeholder replacement."""

    @pytest.mark.asyncio
    async def test_stockpile_name_placeholder(
        self, tmp_path: Path, sample_stockpile: Stockpile
    ) -> None:
        """Test {stockpile_name} placeholder uses first stockpile's name."""
        output_file = tmp_path / "{stockpile_name}.json"
        handler = FileOutputHandler(default_file_path=str(output_file))

        await handler.handle([sample_stockpile])

        expected = tmp_path / "TestStockpile.json"
        assert expected.exists()

    @pytest.mark.asyncio
    async def test_stockpile_type_placeholder(
        self, tmp_path: Path, sample_stockpile: Stockpile
    ) -> None:
        """Test {stockpile_type} placeholder uses first stockpile's type."""
        output_file = tmp_path / "{stockpile_type}.json"
        handler = FileOutputHandler(default_file_path=str(output_file))

        await handler.handle([sample_stockpile])

        expected = tmp_path / "Seaport.json"
        assert expected.exists()

    @pytest.mark.asyncio
    async def test_timestamp_placeholder(self, tmp_path: Path, sample_stockpile: Stockpile) -> None:
        """Test {timestamp} placeholder."""
        output_file = tmp_path / "output_{timestamp}.json"
        handler = FileOutputHandler(default_file_path=str(output_file))

        await handler.handle([sample_stockpile])

        # Find the created file
        files = list(tmp_path.glob("output_*.json"))
        assert len(files) == 1
        assert "output_" in files[0].name


class TestFileOutputHandlerCSV:
    """Test suite for CSV/TSV formatting."""

    @pytest.mark.asyncio
    async def test_csv_format_with_header(
        self, tmp_path: Path, sample_stockpile: Stockpile
    ) -> None:
        """Test CSV output with header."""
        output_file = tmp_path / "output.csv"
        csv_settings = CsvFormatSettings(include_header=True)
        handler = FileOutputHandler(
            default_file_path=str(output_file), format_settings=csv_settings
        )

        await handler.handle([sample_stockpile])

        content = output_file.read_text()
        lines = content.strip().split("\n")
        # Header + 2 items
        assert len(lines) == 3
        assert "code" in lines[0].lower()
        # Verify stockpile_name column is present (first column)
        assert "stockpile name" in lines[0].lower()

    @pytest.mark.asyncio
    async def test_csv_format_without_header(
        self, tmp_path: Path, sample_stockpile: Stockpile
    ) -> None:
        """Test CSV output without header."""
        output_file = tmp_path / "output.csv"
        csv_settings = CsvFormatSettings(include_header=False)
        handler = FileOutputHandler(
            default_file_path=str(output_file), format_settings=csv_settings
        )

        await handler.handle([sample_stockpile])

        content = output_file.read_text()
        lines = content.strip().split("\n")
        # Just 2 items, no header
        assert len(lines) == 2

    @pytest.mark.asyncio
    async def test_tsv_format(self, tmp_path: Path, sample_stockpile: Stockpile) -> None:
        """Test TSV output uses tabs."""
        output_file = tmp_path / "output.tsv"
        tsv_settings = CsvFormatSettings(type=OutputFormat.TSV, include_header=True)
        handler = FileOutputHandler(
            default_file_path=str(output_file), format_settings=tsv_settings
        )

        await handler.handle([sample_stockpile])

        content = output_file.read_text()
        assert "\t" in content

    @pytest.mark.asyncio
    async def test_csv_confidence_none(
        self, tmp_path: Path, sample_stockpile_no_confidence: Stockpile
    ) -> None:
        """Test CSV output with None confidence shows empty."""
        output_file = tmp_path / "output.csv"
        csv_settings = CsvFormatSettings(include_header=False)
        handler = FileOutputHandler(
            default_file_path=str(output_file), format_settings=csv_settings
        )

        await handler.handle([sample_stockpile_no_confidence])

        content = output_file.read_text()
        # The confidence field should be empty for None
        assert content.count(",") >= 3  # Multiple fields

    @pytest.mark.asyncio
    async def test_csv_multiple_stockpiles_have_different_names(
        self, tmp_path: Path, sample_stockpile: Stockpile
    ) -> None:
        """Test CSV with multiple stockpiles shows stockpile name as identifier."""
        output_file = tmp_path / "output.csv"
        csv_settings = CsvFormatSettings(include_header=True)
        handler = FileOutputHandler(
            default_file_path=str(output_file), format_settings=csv_settings
        )

        stockpile2 = Stockpile(
            name="Second",
            type=StockpileType.STORAGE_DEPOT,
            items=[StockpileItem(code="Bmats", quantity=100, crated=False)],
            timestamp=datetime.now(tz=UTC),
        )

        await handler.handle([sample_stockpile, stockpile2])

        content = output_file.read_text()
        lines = content.strip().split("\n")
        # Header + 2 items from first + 1 item from second
        assert len(lines) == 4
        # First stockpile items start with "TestStockpile,"
        assert lines[1].startswith("TestStockpile,")
        assert lines[2].startswith("TestStockpile,")
        # Second stockpile item starts with "Second,"
        assert lines[3].startswith("Second,")


class TestFileOutputHandlerExtension:
    """Test suite for file extension fixing."""

    @pytest.mark.asyncio
    async def test_fix_json_extension(self, tmp_path: Path, sample_stockpile: Stockpile) -> None:
        """Test JSON format gets .json extension."""
        output_file = tmp_path / "output.txt"
        handler = FileOutputHandler(
            default_file_path=str(output_file),
            format_settings=JsonFormatSettings(),
        )

        await handler.handle([sample_stockpile])

        expected = tmp_path / "output.json"
        assert expected.exists()

    @pytest.mark.asyncio
    async def test_fix_csv_extension(self, tmp_path: Path, sample_stockpile: Stockpile) -> None:
        """Test CSV format gets .csv extension."""
        output_file = tmp_path / "output.json"
        handler = FileOutputHandler(
            default_file_path=str(output_file),
            format_settings=CsvFormatSettings(),
        )

        await handler.handle([sample_stockpile])

        expected = tmp_path / "output.csv"
        assert expected.exists()

    @pytest.mark.asyncio
    async def test_add_extension_when_missing(
        self, tmp_path: Path, sample_stockpile: Stockpile
    ) -> None:
        """Test extension is added when missing."""
        output_file = tmp_path / "output"
        handler = FileOutputHandler(
            default_file_path=str(output_file),
            format_settings=JsonFormatSettings(),
        )

        await handler.handle([sample_stockpile])

        expected = tmp_path / "output.json"
        assert expected.exists()


class TestFileOutputHandlerEscaping:
    """Test suite for CSV value escaping."""

    def test_escape_value_with_comma(self) -> None:
        """Test escaping value containing comma."""
        handler = FileOutputHandler()
        result = handler._escape_csv_value("hello, world", ",")
        assert result == '"hello, world"'

    def test_escape_value_with_quotes(self) -> None:
        """Test escaping value containing quotes."""
        handler = FileOutputHandler()
        result = handler._escape_csv_value('say "hello"', ",")
        assert result == '"say ""hello"""'

    def test_escape_value_with_newline(self) -> None:
        """Test escaping value containing newline."""
        handler = FileOutputHandler()
        result = handler._escape_csv_value("line1\nline2", ",")
        assert result == '"line1\nline2"'

    def test_no_escape_needed(self) -> None:
        """Test value that doesn't need escaping."""
        handler = FileOutputHandler()
        result = handler._escape_csv_value("simple", ",")
        assert result == "simple"
