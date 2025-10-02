"""Test runner utilities for the Foxhole Stockpiles test suite.

This module provides utility functions for running tests with different configurations,
including coverage reporting, specific test execution, and mark-based filtering.
"""

import sys

import pytest


def run_tests(args: list[str] | None = None) -> int:
    """Run the test suite with default configuration.

    Args:
        args (list[str] | None): Additional arguments to pass to pytest. If None,
            only default arguments will be used.

    Returns:
        int: Exit code from pytest (0 for success, non-zero for failure).
    """
    test_args = [
        "tests",
        "-v",  # Verbose output
        "--tb=short",  # Shorter traceback format
        "--color=yes",  # Colored output
    ]

    if args:
        test_args.extend(args)

    return pytest.main(test_args)


def run_coverage() -> int:
    """Run tests with coverage reporting enabled.

    This function runs the test suite with coverage analysis, generating both
    terminal output with missing lines and an HTML coverage report.

    Returns:
        int: Exit code from pytest (0 for success, non-zero for failure).
    """
    return run_tests(
        [
            "--cov=foxhole_stockpiles",
            "--cov-report=term-missing",
            "--cov-report=html",
        ]
    )


def run_specific_test(test_path: str) -> int:
    """Run a specific test file or test case.

    Args:
        test_path (str): Path to test file or specific test case. Can be a file path
            like 'tests/test_module.py' or a specific test like
            'tests/test_module.py::TestClass::test_method'.

    Returns:
        int: Exit code from pytest (0 for success, non-zero for failure).
    """
    return run_tests([test_path])


def run_marked_tests(mark: str) -> int:
    """Run tests with a specific pytest mark.

    Args:
        mark (str): Pytest mark to filter by. Common marks include 'unit',
            'integration', 'slow', 'api', etc.

    Returns:
        int: Exit code from pytest (0 for success, non-zero for failure).
    """
    return run_tests([f"-m={mark}"])


if __name__ == "__main__":
    # Simple CLI for running tests
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "coverage":
            sys.exit(run_coverage())
        elif command == "unit":
            sys.exit(run_marked_tests("unit"))
        elif command == "integration":
            sys.exit(run_marked_tests("integration"))
        else:
            # Assume it's a test path
            sys.exit(run_specific_test(command))
    else:
        # Run all tests by default
        sys.exit(run_tests())
