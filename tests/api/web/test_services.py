"""Tests for web services module."""

from unittest.mock import AsyncMock, Mock, patch

import numpy as np
import pytest

from foxhole_stockpiles.api.web.services import IconService
from foxhole_stockpiles.enums.supported_resolution import SupportedResolution


class TestIconService:
    """Tests for IconService."""

    @pytest.fixture
    def mock_template_manager(self) -> Mock:
        """Create a mock template manager."""
        manager = Mock()
        manager.get_available_resolutions.return_value = [
            SupportedResolution.R_1080,
            SupportedResolution.R_1440,
        ]
        return manager

    def test_init(self, mock_template_manager: Mock) -> None:
        """Test IconService initialization."""
        service = IconService(
            template_manager=mock_template_manager,
            default_mod="vanilla",
        )

        assert service._template_manager is mock_template_manager
        assert service._default_mod == "vanilla"
        assert service._icon_cache == {}
        assert service._largest_resolution is None

    def test_init_with_custom_mod(self, mock_template_manager: Mock) -> None:
        """Test IconService initialization with custom mod."""
        service = IconService(
            template_manager=mock_template_manager,
            default_mod="custom_mod",
        )

        assert service._default_mod == "custom_mod"

    @pytest.mark.asyncio
    async def test_get_icon_png_caches_result(self, mock_template_manager: Mock) -> None:
        """Test that icon results are cached."""
        # Create a mock template with an image
        mock_template = Mock()
        mock_template.code = "TestItem"
        mock_template.image = np.zeros((32, 32, 3), dtype=np.uint8)

        # Create mock database
        mock_database = Mock()
        mock_database.get_candidates.return_value = [0]
        mock_database.templates = [mock_template]
        mock_database.get_available_mods.return_value = {"vanilla"}

        mock_template_manager.load_database = AsyncMock(return_value=mock_database)

        service = IconService(template_manager=mock_template_manager)

        # First call
        result1 = await service.get_icon_png(code="TestItem", crated=False)
        assert result1 is not None

        # Second call should use cache (load_database shouldn't be called again)
        mock_template_manager.load_database.reset_mock()
        result2 = await service.get_icon_png(code="TestItem", crated=False)

        assert result1 == result2
        mock_template_manager.load_database.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_icon_png_returns_none_when_not_found(
        self, mock_template_manager: Mock
    ) -> None:
        """Test that None is returned when icon is not found."""
        mock_database = Mock()
        mock_database.get_candidates.return_value = []  # No candidates
        mock_database.templates = []
        mock_database.get_available_mods.return_value = {"vanilla"}

        mock_template_manager.load_database = AsyncMock(return_value=mock_database)

        service = IconService(template_manager=mock_template_manager)

        result = await service.get_icon_png(code="NonExistent", crated=False)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_icon_png_fallback_to_vanilla(self, mock_template_manager: Mock) -> None:
        """Test fallback to vanilla when mod icon not found."""
        mock_template = Mock()
        mock_template.code = "TestItem"
        mock_template.image = np.zeros((32, 32, 3), dtype=np.uint8)

        mock_database = Mock()
        # First call for custom_mod returns empty, second for vanilla returns result
        mock_database.get_candidates.side_effect = [[], [0]]
        mock_database.templates = [mock_template]
        mock_database.get_available_mods.return_value = {"vanilla", "custom_mod"}

        mock_template_manager.load_database = AsyncMock(return_value=mock_database)

        service = IconService(
            template_manager=mock_template_manager,
            default_mod="custom_mod",
        )

        result = await service.get_icon_png(code="TestItem", crated=False)

        assert result is not None
        # Should have been called twice: once for custom_mod, once for vanilla
        assert mock_database.get_candidates.call_count == 2

    @pytest.mark.asyncio
    async def test_get_icon_png_uses_largest_resolution(self, mock_template_manager: Mock) -> None:
        """Test that the largest available resolution is used."""
        mock_template = Mock()
        mock_template.code = "TestItem"
        mock_template.image = np.zeros((32, 32, 3), dtype=np.uint8)

        mock_database = Mock()
        mock_database.get_candidates.return_value = [0]
        mock_database.templates = [mock_template]
        mock_database.get_available_mods.return_value = {"vanilla"}

        mock_template_manager.load_database = AsyncMock(return_value=mock_database)

        service = IconService(template_manager=mock_template_manager)

        await service.get_icon_png(code="TestItem", crated=False)

        # Should use 1440 (the largest)
        mock_template_manager.load_database.assert_called_with(SupportedResolution.R_1440)

    @pytest.mark.asyncio
    async def test_get_icon_png_no_resolutions_available(self, mock_template_manager: Mock) -> None:
        """Test handling when no resolutions are available."""
        mock_template_manager.get_available_resolutions.return_value = []

        service = IconService(template_manager=mock_template_manager)

        result = await service.get_icon_png(code="TestItem", crated=False)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_icon_png_database_not_found(self, mock_template_manager: Mock) -> None:
        """Test handling when database file is not found."""
        mock_template_manager.load_database = AsyncMock(
            side_effect=FileNotFoundError("Database not found")
        )

        service = IconService(template_manager=mock_template_manager)

        result = await service.get_icon_png(code="TestItem", crated=False)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_icon_png_with_crated_flag(self, mock_template_manager: Mock) -> None:
        """Test getting icon with crated flag."""
        mock_template = Mock()
        mock_template.code = "TestItem"
        mock_template.image = np.zeros((32, 32, 3), dtype=np.uint8)

        mock_database = Mock()
        mock_database.get_candidates.return_value = [0]
        mock_database.templates = [mock_template]
        mock_database.get_available_mods.return_value = {"vanilla"}

        mock_template_manager.load_database = AsyncMock(return_value=mock_database)

        service = IconService(template_manager=mock_template_manager)

        result = await service.get_icon_png(code="TestItem", crated=True)

        assert result is not None
        # Verify crated=True was passed to get_candidates
        mock_database.get_candidates.assert_called_with(mod="vanilla", crated=True)

    @pytest.mark.asyncio
    async def test_get_icon_png_with_explicit_mod(self, mock_template_manager: Mock) -> None:
        """Test getting icon with explicit mod parameter."""
        mock_template = Mock()
        mock_template.code = "TestItem"
        mock_template.image = np.zeros((32, 32, 3), dtype=np.uint8)

        mock_database = Mock()
        mock_database.get_candidates.return_value = [0]
        mock_database.templates = [mock_template]
        mock_database.get_available_mods.return_value = {"vanilla", "other_mod"}

        mock_template_manager.load_database = AsyncMock(return_value=mock_database)

        service = IconService(
            template_manager=mock_template_manager,
            default_mod="vanilla",
        )

        result = await service.get_icon_png(code="TestItem", crated=False, mod="other_mod")

        assert result is not None
        # Verify other_mod was used instead of default
        mock_database.get_candidates.assert_called_with(mod="other_mod", crated=False)

    def test_clear_cache(self, mock_template_manager: Mock) -> None:
        """Test cache clearing."""
        service = IconService(template_manager=mock_template_manager)
        service._icon_cache[("test", False, "vanilla")] = b"test_data"
        service._largest_resolution = SupportedResolution.R_1080

        service.clear_cache()

        assert service._icon_cache == {}
        assert service._largest_resolution is None

    @pytest.mark.asyncio
    async def test_get_icon_png_encode_failure(self, mock_template_manager: Mock) -> None:
        """Test handling of PNG encoding failure."""
        mock_template = Mock()
        mock_template.code = "TestItem"
        # Create an invalid image that cv2.imencode might fail on
        mock_template.image = np.array([])  # Empty array

        mock_database = Mock()
        mock_database.get_candidates.return_value = [0]
        mock_database.templates = [mock_template]
        mock_database.get_available_mods.return_value = {"vanilla"}

        mock_template_manager.load_database = AsyncMock(return_value=mock_database)

        service = IconService(template_manager=mock_template_manager)

        with patch("foxhole_stockpiles.api.web.services.cv2.imencode") as mock_encode:
            mock_encode.return_value = (False, None)

            result = await service.get_icon_png(code="TestItem", crated=False)

            assert result is None

    @pytest.mark.asyncio
    async def test_get_icon_png_general_exception(self, mock_template_manager: Mock) -> None:
        """Test handling of general exceptions."""
        mock_template_manager.load_database = AsyncMock(
            side_effect=RuntimeError("Unexpected error")
        )

        service = IconService(template_manager=mock_template_manager)

        result = await service.get_icon_png(code="TestItem", crated=False)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_icon_png_warns_when_mod_not_in_database(
        self, mock_template_manager: Mock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that a warning is logged when configured mod is not in database."""
        import logging

        mock_template = Mock()
        mock_template.code = "TestItem"
        mock_template.image = np.zeros((32, 32, 3), dtype=np.uint8)

        mock_database = Mock()
        # Mod "nonexistent_mod" not in available mods
        mock_database.get_available_mods.return_value = {"vanilla", "other_mod"}
        mock_database.get_candidates.side_effect = [[], [0]]  # Not found in mod, found in vanilla
        mock_database.templates = [mock_template]

        mock_template_manager.load_database = AsyncMock(return_value=mock_database)

        service = IconService(
            template_manager=mock_template_manager,
            default_mod="nonexistent_mod",
        )

        with caplog.at_level(logging.WARNING):
            result = await service.get_icon_png(code="TestItem", crated=False)

        assert result is not None
        assert "nonexistent_mod" in caplog.text
        assert "not found in database" in caplog.text
