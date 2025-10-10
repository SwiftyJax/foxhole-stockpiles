"""Unified CLI tool for Foxhole Stockpiles commands."""

import asyncio
import importlib
import sys
from typing import Any

from foxhole_stockpiles import __version__
from foxhole_stockpiles.models.command_info import CommandInfo


class CLIDispatcher:
    """Dispatcher for unified CLI tool commands."""

    def __init__(self) -> None:
        """Initialize the CLI dispatcher with available commands."""
        self._commands = self._get_available_commands()

    def _get_available_commands(self) -> dict[str, CommandInfo]:
        """Get dictionary of all available commands with their metadata.

        Returns:
            dict[str, CommandInfo]: Dictionary mapping command names to their CommandInfo objects
        """
        return {
            "scanner": CommandInfo(
                description="Scan stockpile screenshots to identify items",
                module="foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner",
                aliases=["scan"],
            ),
            "database-builder": CommandInfo(
                description="Build optimized template databases",
                module="foxhole_stockpiles.commands.database_builder.database_builder",
                aliases=["build"],
            ),
            "generate-templates": CommandInfo(
                description="Generate resolution-specific templates",
                module="foxhole_stockpiles.commands.generate_templates.generate_templates",
                aliases=["generate"],
            ),
            "extract-assets": CommandInfo(
                description="Extract assets from Foxhole PAK files",
                module="foxhole_stockpiles.commands.uasset_extractor.uasset_extractor",
                aliases=["extract"],
            ),
            "inspect": CommandInfo(
                description="Inspect and debug template databases",
                module="foxhole_stockpiles.commands.candidate_inspector.candidate_inspector",
                aliases=["debug"],
            ),
            "server": CommandInfo(
                description="Start the API server",
                module="foxhole_stockpiles.commands.api_server.api_server",
                aliases=["api"],
            ),
        }

    def resolve_command_alias(self, command: str) -> str | None:
        """Resolve command aliases to canonical command names.

        Args:
            command (str): Command name or alias to resolve

        Returns:
            str | None: Canonical command name if found, None if not found
        """
        # Direct match
        if command in self._commands:
            return command

        # Check aliases
        for cmd_name, cmd_info in self._commands.items():
            if command in cmd_info.aliases:
                return cmd_name

        return None

    def get_command_info(self, command: str) -> CommandInfo | None:
        """Get CommandInfo for a given command name or alias.

        Args:
            command (str): Command name or alias

        Returns:
            CommandInfo | None: CommandInfo object if command exists, None otherwise
        """
        canonical_command = self.resolve_command_alias(command)
        if canonical_command is None:
            return None
        return self._commands[canonical_command]

    def list_commands(self) -> dict[str, CommandInfo]:
        """Get all available commands.

        Returns:
            dict[str, CommandInfo]: Dictionary of command names to CommandInfo objects
        """
        return self._commands.copy()

    def get_help(self) -> str:
        """Return comprehensive help information for the unified tool as a string.

        Returns:
            str: Help information string
        """
        lines: list[str] = []
        lines.append("Foxhole Stockpiles - Unified CLI Tool")
        lines.append("=" * 40)
        lines.append("")
        lines.append("Usage: fs <command> [options...]")
        lines.append("")
        lines.append("Available commands:")
        lines.append("")

        for cmd_name, cmd_info in self._commands.items():
            lines.append(f"  {cmd_name:<20} {cmd_info.description}")
            if cmd_info.aliases:
                aliases = ", ".join(cmd_info.aliases)
                lines.append(f"  {'':<20} Aliases: {aliases}")
            lines.append("")

        lines.append("Examples:")
        lines.append("  fs scanner --database db.pkl --image screenshot.png")
        lines.append("  fs scan --help")
        lines.append("  fs database-builder --catalog catalog.json --templates templates/")
        lines.append("  fs extract-assets --catalog catalog.json --pak game.pak")
        lines.append("")
        lines.append("For help with a specific command:")
        lines.append("  fs <command> --help")
        return "\n".join(lines)

    def execute_command(self, command: str) -> Any:
        """Execute a specific command by importing and calling its main function.

        Args:
            command (str): Command name or alias to execute

        Returns:
            Any: Result of the command execution

        Raises:
            ImportError: If the command module cannot be imported
            AttributeError: If the main function is not found in the module
            SystemExit: If the command exits with an error code
        """
        cmd_info = self.get_command_info(command)
        if cmd_info is None:
            available_commands = list(self._commands.keys())
            print(f"Error: Unknown command '{command}'", file=sys.stderr)
            print()
            print("Available commands:")
            for cmd_name in available_commands:
                print(f"  {cmd_name}")
            print()
            print("Use 'fs --help' for more information.")
            sys.exit(1)

        try:
            # Import the module
            module = importlib.import_module(cmd_info.module)

            # Get the main function
            main_func = getattr(module, cmd_info.function)

            # All command main functions are async
            return asyncio.run(main_func())

        except ImportError as e:
            print(f"Error: Failed to import {cmd_info.module}: {e}", file=sys.stderr)
            sys.exit(1)
        except AttributeError as e:
            print(
                f"Error: Function {cmd_info.function} not found in {cmd_info.module}: {e}",
                file=sys.stderr,
            )
            sys.exit(1)


def main() -> None:
    """Main entry point for the unified CLI tool.

    Handles argument parsing and dispatches to the appropriate command.
    """
    dispatcher = CLIDispatcher()

    # DEBUG MODE: Uncomment to use predefined debug arguments
    # sys.argv = [
    #     "fs",
    #     "scanner",
    #     "--database",
    #     "data/foxhole_templates.pkl",
    #     "--image",
    #     "test.png",
    #     "--debug_image",
    # ]

    # Handle no arguments or help requests
    if len(sys.argv) < 2 or sys.argv[1] in ["-h", "--help", "help"]:
        print(dispatcher.get_help())
        return

    command = sys.argv[1]

    # Special handling for version requests
    if command in ["--version", "-v", "version"]:
        print(f"Foxhole Stockpiles v{__version__}")
        return

    # Modify sys.argv to remove the 'fs' part and keep the subcommand arguments
    # This makes individual tools see their normal argument structure
    original_argv = sys.argv.copy()
    canonical_command = dispatcher.resolve_command_alias(command)
    if canonical_command is not None:
        sys.argv = [f"fs-{canonical_command}"] + sys.argv[2:]

    try:
        # Execute the specific command
        result = dispatcher.execute_command(command)

        # Handle return values appropriately
        if result is not None and isinstance(result, dict):
            import json

            print(json.dumps(result, indent=2))

    except SystemExit as e:
        # Let tools exit normally
        sys.exit(e.code)
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Error executing {command}: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        # Restore original argv
        sys.argv = original_argv


if __name__ == "__main__":
    main()
