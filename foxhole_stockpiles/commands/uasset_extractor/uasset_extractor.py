"""PAK file extraction tool for Foxhole game assets.

This module provides functionality to extract game assets from Foxhole PAK files
and convert them to PNG format for use in the stockpile recognition system.
Uses repak for extraction and UModel.exe for conversion.
"""

import argparse
import logging
import multiprocessing
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from foxhole_stockpiles.core.logging import setup_logging
from foxhole_stockpiles.core.utils import load_catalog
from foxhole_stockpiles.models.catalog_item import CatalogItem

DEFAULT_CATALOG = "catalog.json"
DEFAULT_PAK_FILES = (
    r"C:\Program Files (x86)\Steam\steamapps\common\Foxhole\War\Content\Paks"
    r"\War-WindowsNoEditor.pak"
)
DEFAULT_EXTRACTOR = r"C:\repak\repak.exe"
DEFAULT_CONVERTER = r"C:\UModel\umodel.exe"
DEFAULT_OUTPUT = "output"


class PakExtractor:
    """Extract and convert assets from Foxhole PAK files.

    Handles the complete pipeline from PAK extraction to PNG conversion,
    including parallel processing and error handling. Supports multiple
    PAK files for mod compatibility.
    """

    def __init__(
        self,
        catalog_file: str = DEFAULT_CATALOG,
        pak_files: str | list[str] = DEFAULT_PAK_FILES,
        extractor_tool: str = DEFAULT_EXTRACTOR,
        converter_tool: str = DEFAULT_CONVERTER,
        output_dir: str = DEFAULT_OUTPUT,
        log_file: str = "",
    ) -> None:
        """Initialize the PAK extractor with default paths and tools.

        Args:
            catalog_file (str): Path to the catalog.json file.
            pak_files (str | list[str]): Path(s) to PAK file(s). Can be a single path or a list.
            extractor_tool (str): Path to the repak.exe tool for extraction.
            converter_tool (str): Path to the umodel.exe tool for conversion.
            output_dir (str): Directory where converted PNG files will be saved.
            log_file (str): Optional path to log file for logging output.

        Raises:
            ValueError: If any of the parameters but log_file is empty.
            FileNotFoundError: If any specified file does not exist.
        """
        if not catalog_file:
            raise ValueError("catalog_file cannot be an empty string")

        if not pak_files:
            raise ValueError("pak_files cannot be empty")

        if not extractor_tool:
            raise ValueError("extractor_tool cannot be an empty string")

        if not converter_tool:
            raise ValueError("converter_tool cannot be an empty string")

        if not output_dir:
            raise ValueError("output_dir cannot be an empty string")

        self.catalog_file = Path(catalog_file).resolve()
        self.extractor_tool = Path(extractor_tool).resolve()
        self.converter_tool = Path(converter_tool).resolve()
        self.output_dir = Path(output_dir).resolve()

        if not self.catalog_file.exists():
            raise FileNotFoundError(f"Catalog file not found: {self.catalog_file}")

        if not self.extractor_tool.exists():
            raise FileNotFoundError(f"Extractor tool not found: {self.extractor_tool}")

        if not self.converter_tool.exists():
            raise FileNotFoundError(f"Converter tool not found: {self.converter_tool}")

        if isinstance(pak_files, str):
            self.pak_files = [Path(pak_files).resolve()]
        else:
            self.pak_files = [Path(pak_file).resolve() for pak_file in pak_files]

        # Validate that all pak files exist (optional but recommended)
        for pak_file in self.pak_files:
            if not pak_file.exists():
                raise FileNotFoundError(f"PAK file not found: {pak_file}")

        # Setup logging
        setup_logging(log_file=log_file)
        self._logger = logging.getLogger(__name__)
        self._logger.info("Using PAK files: %s", self.pak_files)

        self.output_dir.mkdir(parents=True, exist_ok=True)

    def extract_single_file(self, file_path: str, temp_dir: str) -> bool:
        """Extract a single file from the PAK files to temporary directory.

        Tries each PAK file in order until the file is found and extracted.

        Args:
            file_path (str): The path of the file to extract.
            temp_dir (str): The temporary directory to extract files to.

        Returns:
            bool: True if extraction was successful, False otherwise.
        """
        for pak_file in self.pak_files:
            # Create a unique subdirectory for this PAK to avoid conflicts
            pak_name = Path(pak_file).stem
            pak_extract_dir = Path(temp_dir) / pak_name

            # Ensure output directory ends with / for repak
            output_dir_str = str(pak_extract_dir) + "/"

            command = [
                str(self.extractor_tool),
                "unpack",
                "-o",
                output_dir_str,
                "--include",
                file_path,
                "-q",
                str(pak_file),
            ]

            try:
                self._logger.debug("Extracting %s from %s", file_path, pak_file)
                process = subprocess.run(command, capture_output=True, text=True)

                if process.returncode == 0:
                    # Check if the specific file was extracted
                    extracted_file_path = pak_extract_dir / file_path
                    if extracted_file_path.exists():
                        self._logger.info("Successfully extracted: %s", file_path)
                        return True

                    self._logger.debug("File %s not found in %s", file_path, pak_file)
                    continue

                self._logger.debug("Failed to extract from %s (file not in PAK)", pak_file)
                continue

            except Exception as e:
                self._logger.error("Error extracting %s from %s: %s", file_path, pak_file, e)
                continue

        # If we get here, file wasn't found in any PAK
        self._logger.error("Failed to extract %s from any PAK file", file_path)
        return False

    def convert_to_png(self, file_path: str, temp_dir: str) -> bool:
        """Convert extracted file to PNG using UModel.

        Args:
            file_path (str): The path of the file to convert.
            temp_dir (str): The temporary directory where the file is located.

        Returns:
            bool: True if conversion was successful, False otherwise.
        """
        if self._try_convert_with_version(file_path=file_path, temp_dir=temp_dir):
            return True

        # If all versions fail, log the issue
        self._logger.error("Failed to convert %s with any UE version", file_path)
        return False

    def _try_convert_with_version(
        self, file_path: str, temp_dir: str, ue_version: str = "ue4.27"
    ) -> bool:
        """Try to convert file with specific UE version.

        Args:
            file_path (str): The path of the file to convert.
            temp_dir (str): The temporary directory where the file is located.
            ue_version (str): The Unreal Engine version to use for conversion. Defaults to "ue4.27".

        Returns:
            bool: True if conversion succeeded, False otherwise.
        """
        try:
            # Find the PAK directory that contains the extracted file
            temp_path = Path(temp_dir)
            pak_root_dir = None

            for pak_dir in temp_path.iterdir():
                if pak_dir.is_dir():
                    potential_file = pak_dir / file_path
                    if potential_file.exists():
                        pak_root_dir = pak_dir
                        break

            if not pak_root_dir:
                self._logger.error("Could not find extracted file: %s", file_path)
                return False

            command = [
                str(self.converter_tool),
                f"-path={pak_root_dir}",
                f"-game={ue_version}",
                "-png",
                "-export",
                file_path,
                f"-out={pak_root_dir}\\War\\Content\\",
            ]

            self._logger.debug("Trying conversion with %s: %s", ue_version, file_path)
            process = subprocess.run(command, capture_output=True, text=True)

            if process.returncode == 0:
                # Handle the output path conversion
                file_path_obj = Path(file_path)
                png_name = file_path_obj.with_suffix(".png")
                converted_path = pak_root_dir / png_name
                output_path = Path(self.output_dir) / png_name

                # Ensure output directory exists
                output_path.parent.mkdir(parents=True, exist_ok=True)

                # Move the converted file if it exists
                if converted_path.exists():
                    shutil.move(str(converted_path), str(output_path))
                    self._logger.info("Successfully converted with %s: %s", ue_version, png_name)
                    return True
                else:
                    self._logger.debug(
                        "Converted file not found at expected path: %s", converted_path
                    )
                    return False
            else:
                self._logger.debug("Conversion failed with %s for %s", ue_version, file_path)
                return False

        except Exception as e:
            self._logger.debug("Error converting %s with %s: %s", file_path, ue_version, e)
            return False

    def get_files_to_extract(self) -> set[str]:
        """Get all unique files that need to be extracted from the catalog.

        Returns:
            set[str]: A set of unique file paths to extract.
        """
        catalog: list[CatalogItem] = load_catalog(self.catalog_file)
        if not catalog:
            return set()

        # Issdsad
        files_to_extract = set()

        # Add the crate icon file
        files_to_extract.add("War/Content/Textures/UI/Menus/IconFilterCrates.uasset")

        for item in catalog:
            if not item.icon_path:
                self._logger.warning("Item %s has no icon path, skipping", item.code)
                continue

            files_to_extract.add(f"{item.icon_path}.uasset")
            if item.subicon_path:
                files_to_extract.add(f"{item.subicon_path}.uasset")

        self._logger.info("Found %d unique files to process", len(files_to_extract))
        return files_to_extract

    def process_files(self, max_workers: int | None = None) -> bool:
        """Extract and convert all files.

        Args:
            max_workers (int | None): Number of parallel operations. Defaults to None, which uses
                the CPU count.

        Returns:
            bool: True if all operations were successful, False otherwise.
        """
        files_to_extract = self.get_files_to_extract()

        if not files_to_extract:
            self._logger.warning("No files found to extract")
            return False

        # Use CPU count if max_workers is not specified
        if max_workers is None:
            max_workers = multiprocessing.cpu_count()
            self._logger.info("Using %d workers based on CPU count", max_workers)

        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            self._logger.info("Created temporary directory: %s", temp_dir)

            # Extract files individually
            self._logger.info("Starting extraction of %d files...", len(files_to_extract))
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                extract_results = list(
                    executor.map(
                        lambda f: self.extract_single_file(f, temp_dir),
                        files_to_extract,
                    )
                )

            successful_extractions = sum(1 for result in extract_results if result)
            failed_extractions = sum(1 for result in extract_results if not result)

            self._logger.info(
                "Extracted %d/%d files successfully", successful_extractions, len(files_to_extract)
            )

            if successful_extractions == 0:
                self._logger.error("No files were extracted successfully")
                return False

            # Convert files to PNG
            self._logger.info("Starting conversion to PNG...")
            # Only convert files that were successfully extracted
            files_to_convert = [f for i, f in enumerate(files_to_extract) if extract_results[i]]

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                convert_results = list(
                    executor.map(lambda f: self.convert_to_png(f, temp_dir), files_to_convert)
                )

            successful_conversions = sum(1 for result in convert_results if result)
            failed_conversions = sum(1 for result in convert_results if not result)

            # Log summary
            self._logger.info("\nProcessing Summary:")
            self._logger.info("Total catalog files: %d", len(files_to_extract))
            self._logger.info("Successful extractions: %d", successful_extractions)
            self._logger.info("Failed extractions: %d", failed_extractions)
            self._logger.info("Successful conversions: %d", successful_conversions)
            self._logger.info("Failed conversions: %d", failed_conversions)

            # Consider it successful if we converted at least some files
            return successful_conversions > 0


def main() -> None:
    """Command-line interface for the PAK extraction tool.

    Parses command-line arguments and runs the extraction process.
    Exits with code 1 if any operations fail, 0 if all succeed.
    """
    parser = argparse.ArgumentParser(
        description="Extract and convert files from a PAK file based on catalog.json",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--pak",
        action="append",
        help="Path to PAK file(s). Can be specified multiple times for mod support. "
        "Default: Foxhole War-WindowsNoEditor.pak",
    )
    parser.add_argument(
        "--catalog",
        help="Path to the catalog.json file",
        default=DEFAULT_CATALOG,
    )
    parser.add_argument(
        "--extractor-tool",
        help="Path to repak.exe",
        default=DEFAULT_EXTRACTOR,
    )
    parser.add_argument(
        "--converter-tool",
        help="Path to umodel.exe",
        default=DEFAULT_CONVERTER,
    )
    parser.add_argument(
        "--output",
        help="Output directory for converted files",
        default=DEFAULT_OUTPUT,
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Number of parallel operations (default: cpu count)",
    )
    parser.add_argument("--logfile", help="Path to log file (default: console only)")

    args = parser.parse_args()

    try:
        extractor = PakExtractor(
            pak_files=args.pak or DEFAULT_PAK_FILES,
            catalog_file=args.catalog,
            extractor_tool=args.extractor_tool,
            converter_tool=args.converter_tool,
            output_dir=args.output,
            log_file=args.logfile,
        )
    except (ValueError, FileNotFoundError) as e:
        print(f"Error: {e}")
        exit(1)

    success = extractor.process_files(max_workers=args.workers)
    if not success:
        print("\nSome operations failed. Check the logs above for details.")
        exit(1)
    else:
        print("\nAll operations completed successfully!")


if __name__ == "__main__":
    main()
