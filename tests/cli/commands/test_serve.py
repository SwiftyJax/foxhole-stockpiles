"""Tests for the ``fs serve`` command (``foxhole_stockpiles.cli.commands.serve``)."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from foxhole_stockpiles.cli.commands import serve

runner = CliRunner()


class TestServeCommand:
    """Test suite for the ``serve`` command via CliRunner."""

    @patch("foxhole_stockpiles.cli.commands.serve.uvicorn.run")
    def test_starts_server_with_defaults(self, mock_run: MagicMock) -> None:
        """Invokes uvicorn with the configured app path.

        Args:
            mock_run (MagicMock): Mocked uvicorn.run.
        """
        result = runner.invoke(serve.app, [])

        assert result.exit_code == 0
        mock_run.assert_called_once()
        assert mock_run.call_args.args[0] == "foxhole_stockpiles.api.server:app"

    @patch("foxhole_stockpiles.cli.commands.serve.uvicorn.run")
    def test_overrides_host_and_port(self, mock_run: MagicMock) -> None:
        """Forwards explicit host and port to uvicorn.

        Args:
            mock_run (MagicMock): Mocked uvicorn.run.
        """
        result = runner.invoke(serve.app, ["--host", "0.0.0.0", "--port", "9999"])

        assert result.exit_code == 0
        call_kwargs = mock_run.call_args.kwargs
        assert call_kwargs["host"] == "0.0.0.0"
        assert call_kwargs["port"] == 9999

    def test_invalid_log_level_exits_two(self) -> None:
        """An invalid log level exits with code 2."""
        result = runner.invoke(serve.app, ["--log-level", "bogus"])

        assert result.exit_code == 2

    @patch("foxhole_stockpiles.cli.commands.serve.uvicorn.run")
    def test_startup_failure_exits_one(self, mock_run: MagicMock) -> None:
        """A uvicorn startup failure exits with code 1.

        Args:
            mock_run (MagicMock): Mocked uvicorn.run.
        """
        mock_run.side_effect = RuntimeError("cannot bind")

        result = runner.invoke(serve.app, [])

        assert result.exit_code == 1
