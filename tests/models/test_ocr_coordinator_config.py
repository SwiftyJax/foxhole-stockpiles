"""Tests for models.ocr_coordinator_config module.

This module contains comprehensive tests for the OCRCoordinatorConfig model,
including field validation, model validation, and configuration retrieval.
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from foxhole_stockpiles.enums.item_faction import ItemFaction
from foxhole_stockpiles.enums.supported_resolution import SupportedResolution
from foxhole_stockpiles.models.ocr_coordinator_config import OCRCoordinatorConfig


class TestOCRCoordinatorConfigInitialization:
    """Test suite for OCRCoordinatorConfig initialization.

    This class contains tests for creating OCRCoordinatorConfig instances
    with various parameter combinations.
    """

    def test_initialization_with_defaults(self, tmp_path: Path) -> None:
        """Test initialization with default values.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        # Create a mock database file
        db_file = tmp_path / "database.pkl"
        db_file.touch()

        config = OCRCoordinatorConfig(database_path=db_file)

        assert config.database_path == db_file
        assert config.confidence_threshold == 0.85
        assert config.early_exit_threshold == 0.95
        assert config.faction_filter is None
        assert config.custom_model == "renner_numbers"
        assert config.tessdata_path == "./tessdata"
        assert config.debug_mode is False
        assert config.screenshots_folder == ""
        assert config.max_ncc_candidates == 25
        assert config.phash_threshold == 12

    def test_initialization_with_custom_values(self, tmp_path: Path) -> None:
        """Test initialization with custom values.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_file = tmp_path / "custom.pkl"
        db_file.touch()

        config = OCRCoordinatorConfig(
            database_path=db_file,
            confidence_threshold=0.75,
            early_exit_threshold=0.98,
            faction_filter=ItemFaction.COLONIALS,
            custom_model="my_model",
            tessdata_path="/custom/tessdata",
            debug_mode=True,
            screenshots_folder="screenshots",
            max_ncc_candidates=50,
            phash_threshold=15,
        )

        assert config.database_path == db_file
        assert config.confidence_threshold == 0.75
        assert config.early_exit_threshold == 0.98
        assert config.faction_filter == ItemFaction.COLONIALS
        assert config.custom_model == "my_model"
        assert config.tessdata_path == "/custom/tessdata"
        assert config.debug_mode is True
        assert config.screenshots_folder == "screenshots"
        assert config.max_ncc_candidates == 50
        assert config.phash_threshold == 15

    def test_initialization_with_confidence_by_resolution(self, tmp_path: Path) -> None:
        """Test initialization with resolution-specific confidence values.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_file = tmp_path / "database.pkl"
        db_file.touch()

        confidence_dict = {
            SupportedResolution.R_720: 0.70,
            SupportedResolution.R_1080: 0.85,
            SupportedResolution.R_2160: 0.90,
        }

        config = OCRCoordinatorConfig(
            database_path=db_file, confidence_by_resolution=confidence_dict
        )

        assert config.confidence_by_resolution == confidence_dict


class TestValidateDatabasePath:
    """Test suite for database_path field validation.

    This class contains tests for the validate_database_path validator.
    """

    def test_validate_database_path_exists_and_is_file(self, tmp_path: Path) -> None:
        """Test validation passes when database path exists and is a file.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_file = tmp_path / "valid.pkl"
        db_file.touch()

        config = OCRCoordinatorConfig(database_path=db_file)

        assert config.database_path == db_file

    def test_validate_database_path_does_not_exist(self, tmp_path: Path) -> None:
        """Test validation fails when database path does not exist.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_file = tmp_path / "nonexistent.pkl"

        with pytest.raises(ValidationError) as exc_info:
            OCRCoordinatorConfig(database_path=db_file)

        assert "Database path does not exist" in str(exc_info.value)

    def test_validate_database_path_is_directory(self, tmp_path: Path) -> None:
        """Test validation fails when database path is a directory.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_dir = tmp_path / "database_dir"
        db_dir.mkdir()

        with pytest.raises(ValidationError) as exc_info:
            OCRCoordinatorConfig(database_path=db_dir)

        assert "Database path is not a file" in str(exc_info.value)


class TestValidateConfidenceByResolution:
    """Test suite for confidence_by_resolution field validation.

    This class contains tests for the validate_confidence_by_resolution validator.
    """

    def test_validate_confidence_by_resolution_valid_values(self, tmp_path: Path) -> None:
        """Test validation passes with valid confidence values.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_file = tmp_path / "database.pkl"
        db_file.touch()

        confidence_dict = {
            SupportedResolution.R_720: 0.70,
            SupportedResolution.R_1080: 0.85,
            SupportedResolution.R_2160: 1.0,
        }

        config = OCRCoordinatorConfig(
            database_path=db_file, confidence_by_resolution=confidence_dict
        )

        assert config.confidence_by_resolution == confidence_dict

    def test_validate_confidence_by_resolution_minimum_value(self, tmp_path: Path) -> None:
        """Test validation passes with minimum confidence value (0.0).

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_file = tmp_path / "database.pkl"
        db_file.touch()

        confidence_dict = {SupportedResolution.R_1080: 0.0}

        config = OCRCoordinatorConfig(
            database_path=db_file, confidence_by_resolution=confidence_dict
        )

        assert config.confidence_by_resolution[SupportedResolution.R_1080] == 0.0

    def test_validate_confidence_by_resolution_below_minimum(self, tmp_path: Path) -> None:
        """Test validation fails with confidence value below 0.0.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_file = tmp_path / "database.pkl"
        db_file.touch()

        confidence_dict = {SupportedResolution.R_1080: -0.1}

        with pytest.raises(ValidationError) as exc_info:
            OCRCoordinatorConfig(database_path=db_file, confidence_by_resolution=confidence_dict)

        assert "must be between 0.0 and 1.0" in str(exc_info.value)

    def test_validate_confidence_by_resolution_above_maximum(self, tmp_path: Path) -> None:
        """Test validation fails with confidence value above 1.0.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_file = tmp_path / "database.pkl"
        db_file.touch()

        confidence_dict = {SupportedResolution.R_1080: 1.5}

        with pytest.raises(ValidationError) as exc_info:
            OCRCoordinatorConfig(database_path=db_file, confidence_by_resolution=confidence_dict)

        assert "must be between 0.0 and 1.0" in str(exc_info.value)

    def test_validate_confidence_by_resolution_multiple_invalid(self, tmp_path: Path) -> None:
        """Test validation fails when multiple confidence values are invalid.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_file = tmp_path / "database.pkl"
        db_file.touch()

        confidence_dict = {
            SupportedResolution.R_720: -0.5,
            SupportedResolution.R_1080: 0.85,
            SupportedResolution.R_2160: 2.0,
        }

        with pytest.raises(ValidationError) as exc_info:
            OCRCoordinatorConfig(database_path=db_file, confidence_by_resolution=confidence_dict)

        # Should fail on first invalid value encountered
        assert "must be between 0.0 and 1.0" in str(exc_info.value)


class TestValidateModel:
    """Test suite for model-level validation.

    This class contains tests for the validate_model validator
    that checks relationships between multiple fields.
    """

    def test_validate_model_early_exit_greater_than_confidence(self, tmp_path: Path) -> None:
        """Test validation passes when early_exit > confidence_threshold.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_file = tmp_path / "database.pkl"
        db_file.touch()

        config = OCRCoordinatorConfig(
            database_path=db_file, confidence_threshold=0.80, early_exit_threshold=0.95
        )

        assert config.confidence_threshold == 0.80
        assert config.early_exit_threshold == 0.95

    def test_validate_model_early_exit_equal_to_confidence(self, tmp_path: Path) -> None:
        """Test validation fails when early_exit equals confidence_threshold.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_file = tmp_path / "database.pkl"
        db_file.touch()

        with pytest.raises(ValidationError) as exc_info:
            OCRCoordinatorConfig(
                database_path=db_file,
                confidence_threshold=0.85,
                early_exit_threshold=0.85,
            )

        assert "Early exit threshold must be greater than confidence threshold" in str(
            exc_info.value
        )

    def test_validate_model_early_exit_less_than_confidence(self, tmp_path: Path) -> None:
        """Test validation fails when early_exit < confidence_threshold.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_file = tmp_path / "database.pkl"
        db_file.touch()

        with pytest.raises(ValidationError) as exc_info:
            OCRCoordinatorConfig(
                database_path=db_file,
                confidence_threshold=0.90,
                early_exit_threshold=0.85,
            )

        assert "Early exit threshold must be greater than confidence threshold" in str(
            exc_info.value
        )


class TestFieldConstraints:
    """Test suite for Pydantic field constraints.

    This class contains tests for built-in Pydantic constraints
    like ge, le on various fields.
    """

    def test_confidence_threshold_below_minimum(self, tmp_path: Path) -> None:
        """Test confidence_threshold validation fails below 0.0.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_file = tmp_path / "database.pkl"
        db_file.touch()

        with pytest.raises(ValidationError) as exc_info:
            OCRCoordinatorConfig(database_path=db_file, confidence_threshold=-0.1)

        assert "greater than or equal to 0" in str(exc_info.value)

    def test_confidence_threshold_above_maximum(self, tmp_path: Path) -> None:
        """Test confidence_threshold validation fails above 1.0.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_file = tmp_path / "database.pkl"
        db_file.touch()

        with pytest.raises(ValidationError) as exc_info:
            OCRCoordinatorConfig(database_path=db_file, confidence_threshold=1.5)

        assert "less than or equal to 1" in str(exc_info.value)

    def test_early_exit_threshold_below_minimum(self, tmp_path: Path) -> None:
        """Test early_exit_threshold validation fails below 0.0.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_file = tmp_path / "database.pkl"
        db_file.touch()

        with pytest.raises(ValidationError) as exc_info:
            OCRCoordinatorConfig(database_path=db_file, early_exit_threshold=-0.1)

        assert "greater than or equal to 0" in str(exc_info.value)

    def test_early_exit_threshold_above_maximum(self, tmp_path: Path) -> None:
        """Test early_exit_threshold validation fails above 1.0.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_file = tmp_path / "database.pkl"
        db_file.touch()

        with pytest.raises(ValidationError) as exc_info:
            OCRCoordinatorConfig(database_path=db_file, early_exit_threshold=1.5)

        assert "less than or equal to 1" in str(exc_info.value)

    def test_max_ncc_candidates_below_minimum(self, tmp_path: Path) -> None:
        """Test max_ncc_candidates validation fails below 1.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_file = tmp_path / "database.pkl"
        db_file.touch()

        with pytest.raises(ValidationError) as exc_info:
            OCRCoordinatorConfig(database_path=db_file, max_ncc_candidates=0)

        assert "greater than or equal to 1" in str(exc_info.value)

    def test_phash_threshold_below_minimum(self, tmp_path: Path) -> None:
        """Test phash_threshold validation fails below 0.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_file = tmp_path / "database.pkl"
        db_file.touch()

        with pytest.raises(ValidationError) as exc_info:
            OCRCoordinatorConfig(database_path=db_file, phash_threshold=-1)

        assert "greater than or equal to 0" in str(exc_info.value)


class TestGetConfidenceThreshold:
    """Test suite for get_confidence_threshold method.

    This class contains tests for retrieving resolution-specific
    or default confidence thresholds.
    """

    def test_get_confidence_threshold_with_specific_resolution(self, tmp_path: Path) -> None:
        """Test getting confidence threshold for specific resolution.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_file = tmp_path / "database.pkl"
        db_file.touch()

        confidence_dict = {
            SupportedResolution.R_720: 0.70,
            SupportedResolution.R_1080: 0.85,
        }

        config = OCRCoordinatorConfig(
            database_path=db_file, confidence_by_resolution=confidence_dict
        )

        assert config.get_confidence_threshold(SupportedResolution.R_1080) == 0.85

    def test_get_confidence_threshold_with_default_fallback(self, tmp_path: Path) -> None:
        """Test getting confidence threshold falls back to default.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_file = tmp_path / "database.pkl"
        db_file.touch()

        confidence_dict = {SupportedResolution.R_720: 0.70}

        config = OCRCoordinatorConfig(
            database_path=db_file,
            confidence_threshold=0.80,
            confidence_by_resolution=confidence_dict,
        )

        # 1080 not in dict, should return default
        assert config.get_confidence_threshold(SupportedResolution.R_1080) == 0.80

    def test_get_confidence_threshold_with_empty_dict(self, tmp_path: Path) -> None:
        """Test getting confidence threshold with empty resolution dict.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_file = tmp_path / "database.pkl"
        db_file.touch()

        config = OCRCoordinatorConfig(database_path=db_file, confidence_threshold=0.90)

        assert config.get_confidence_threshold(SupportedResolution.R_2160) == 0.90


class TestModelConfigSettings:
    """Test suite for model configuration settings.

    This class contains tests for Pydantic model configuration
    like str_strip_whitespace, validate_assignment, and extra fields.
    """

    def test_str_strip_whitespace(self, tmp_path: Path) -> None:
        """Test that string fields have whitespace stripped.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_file = tmp_path / "database.pkl"
        db_file.touch()

        config = OCRCoordinatorConfig(database_path=db_file, custom_model="  my_model  ")

        assert config.custom_model == "my_model"

    def test_extra_fields_forbidden(self, tmp_path: Path) -> None:
        """Test that extra fields are forbidden.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_file = tmp_path / "database.pkl"
        db_file.touch()

        with pytest.raises(ValidationError) as exc_info:
            OCRCoordinatorConfig(database_path=db_file, unknown_field="value")  # type: ignore

        assert "Extra inputs are not permitted" in str(exc_info.value)

    def test_validate_assignment(self, tmp_path: Path) -> None:
        """Test that assignment validation is enabled.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_file = tmp_path / "database.pkl"
        db_file.touch()

        config = OCRCoordinatorConfig(database_path=db_file)

        # Try to assign invalid value after creation
        with pytest.raises(ValidationError):
            config.confidence_threshold = 1.5  # Above maximum
