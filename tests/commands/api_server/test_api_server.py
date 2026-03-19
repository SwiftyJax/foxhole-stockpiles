"""Tests for the API server command."""

from unittest.mock import Mock, patch

from foxhole_stockpiles.commands.api_server.api_server import main


class TestAPIServerMain:
    """Test cases for the API server main function."""

    @patch("foxhole_stockpiles.commands.api_server.api_server.uvicorn.run")
    @patch("foxhole_stockpiles.commands.api_server.api_server.get_settings")
    def test_main_with_default_settings(
        self, mock_get_settings: Mock, mock_uvicorn_run: Mock
    ) -> None:
        """Test main function uses settings defaults when no CLI args provided.

        Args:
            mock_get_settings (Mock): Mocked get_settings function.
            mock_uvicorn_run (Mock): Mocked uvicorn.run function.
        """
        # Mock settings
        mock_settings = Mock()
        mock_settings.api_server.host = "127.0.0.1"
        mock_settings.api_server.port = 8000
        mock_settings.api_server.workers = 1
        mock_settings.api_server.reload = False
        mock_settings.api_server.log_level = "info"
        mock_get_settings.return_value = mock_settings

        # Mock sys.argv to simulate no arguments
        with patch("sys.argv", ["fs server"]):
            result = main()

        # Verify uvicorn.run was called with settings defaults
        mock_uvicorn_run.assert_called_once_with(
            "foxhole_stockpiles.api.server:app",
            host="127.0.0.1",
            port=8000,
            workers=1,
            reload=False,
            log_level="info",
        )
        assert result == 0

    @patch("foxhole_stockpiles.commands.api_server.api_server.uvicorn.run")
    @patch("foxhole_stockpiles.commands.api_server.api_server.get_settings")
    def test_main_with_cli_overrides(self, mock_get_settings: Mock, mock_uvicorn_run: Mock) -> None:
        """Test main function with CLI arguments overriding settings.

        Args:
            mock_get_settings (Mock): Mocked get_settings function.
            mock_uvicorn_run (Mock): Mocked uvicorn.run function.
        """
        # Mock settings
        mock_settings = Mock()
        mock_settings.api_server.host = "127.0.0.1"
        mock_settings.api_server.port = 8000
        mock_settings.api_server.workers = 1
        mock_settings.api_server.reload = False
        mock_settings.api_server.log_level = "info"
        mock_get_settings.return_value = mock_settings

        # Mock sys.argv with custom arguments
        with patch(
            "sys.argv",
            [
                "fs server",
                "--host",
                "0.0.0.0",
                "--port",
                "9000",
                "--workers",
                "4",
                "--log-level",
                "debug",
            ],
        ):
            result = main()

        # Verify uvicorn.run was called with CLI overrides
        mock_uvicorn_run.assert_called_once_with(
            "foxhole_stockpiles.api.server:app",
            host="0.0.0.0",
            port=9000,
            workers=4,
            reload=False,
            log_level="debug",
        )
        assert result == 0

    @patch("foxhole_stockpiles.commands.api_server.api_server.uvicorn.run")
    @patch("foxhole_stockpiles.commands.api_server.api_server.get_settings")
    def test_main_with_reload_flag(self, mock_get_settings: Mock, mock_uvicorn_run: Mock) -> None:
        """Test main function with --reload flag.

        Args:
            mock_get_settings (Mock): Mocked get_settings function.
            mock_uvicorn_run (Mock): Mocked uvicorn.run function.
        """
        # Mock settings
        mock_settings = Mock()
        mock_settings.api_server.host = "127.0.0.1"
        mock_settings.api_server.port = 8000
        mock_settings.api_server.workers = 1
        mock_settings.api_server.reload = False
        mock_settings.api_server.log_level = "info"
        mock_get_settings.return_value = mock_settings

        # Mock sys.argv with --reload flag
        with patch("sys.argv", ["fs server", "--reload"]):
            result = main()

        # Verify reload is True
        call_kwargs = mock_uvicorn_run.call_args[1]
        assert call_kwargs["reload"] is True
        assert result == 0

    @patch("foxhole_stockpiles.commands.api_server.api_server.uvicorn.run")
    @patch("foxhole_stockpiles.commands.api_server.api_server.get_settings")
    def test_main_handles_uvicorn_exception(
        self, mock_get_settings: Mock, mock_uvicorn_run: Mock
    ) -> None:
        """Test main function handles uvicorn exceptions.

        Args:
            mock_get_settings (Mock): Mocked get_settings function.
            mock_uvicorn_run (Mock): Mocked uvicorn.run function.
        """
        # Mock settings
        mock_settings = Mock()
        mock_settings.api_server.host = "127.0.0.1"
        mock_settings.api_server.port = 8000
        mock_settings.api_server.workers = 1
        mock_settings.api_server.reload = False
        mock_settings.api_server.log_level = "info"
        mock_get_settings.return_value = mock_settings

        # Make uvicorn.run raise an exception
        mock_uvicorn_run.side_effect = Exception("Port already in use")

        # Mock sys.argv
        with patch("sys.argv", ["fs server"]):
            result = main()

        # Verify error handling
        assert result == 1

    @patch("foxhole_stockpiles.commands.api_server.api_server.uvicorn.run")
    @patch("foxhole_stockpiles.commands.api_server.api_server.get_settings")
    def test_main_partial_cli_overrides(
        self, mock_get_settings: Mock, mock_uvicorn_run: Mock
    ) -> None:
        """Test main function with partial CLI overrides uses settings for rest.

        Args:
            mock_get_settings (Mock): Mocked get_settings function.
            mock_uvicorn_run (Mock): Mocked uvicorn.run function.
        """
        # Mock settings with non-default values
        mock_settings = Mock()
        mock_settings.api_server.host = "0.0.0.0"
        mock_settings.api_server.port = 8080
        mock_settings.api_server.workers = 4
        mock_settings.api_server.reload = True
        mock_settings.api_server.log_level = "debug"
        mock_get_settings.return_value = mock_settings

        # Mock sys.argv with only port override
        with patch("sys.argv", ["fs server", "--port", "9000"]):
            result = main()

        # Verify CLI port is used, but other settings come from config
        mock_uvicorn_run.assert_called_once_with(
            "foxhole_stockpiles.api.server:app",
            host="0.0.0.0",  # From settings
            port=9000,  # From CLI
            workers=4,  # From settings
            reload=True,  # From settings
            log_level="debug",  # From settings
        )
        assert result == 0
