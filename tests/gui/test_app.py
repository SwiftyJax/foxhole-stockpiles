"""Tests for GUI application launcher."""

from unittest.mock import MagicMock, patch

from foxhole_stockpiles.gui.app import _load_language_from_settings, launch_gui


def test_launch_gui_creates_application() -> None:
    """Test launch_gui creates QApplication."""
    with patch("foxhole_stockpiles.gui.app.QApplication") as mock_app_class:
        mock_app = MagicMock()
        mock_app_class.return_value = mock_app
        mock_app.exec.return_value = 0

        with patch("foxhole_stockpiles.gui.app.MainWindow") as mock_window_class:
            mock_window = MagicMock()
            mock_window_class.return_value = mock_window

            with patch("sys.exit"):
                launch_gui()

                # Should create QApplication
                mock_app_class.assert_called_once()

                # Should set application metadata
                mock_app.setApplicationName.assert_called_once_with("FS")
                mock_app.setOrganizationName.assert_called_once_with("FS")
                mock_app.setApplicationVersion.assert_called_once()


def test_launch_gui_creates_main_window() -> None:
    """Test launch_gui creates and shows MainWindow."""
    with patch("foxhole_stockpiles.gui.app.QApplication") as mock_app_class:
        mock_app = MagicMock()
        mock_app_class.return_value = mock_app
        mock_app.exec.return_value = 0

        with patch("foxhole_stockpiles.gui.app.MainWindow") as mock_window_class:
            mock_window = MagicMock()
            mock_window_class.return_value = mock_window

            with patch("sys.exit"):
                launch_gui()

                # Should create MainWindow
                mock_window_class.assert_called_once()

                # Should show window
                mock_window.show.assert_called_once()


def test_launch_gui_starts_event_loop() -> None:
    """Test launch_gui starts Qt event loop."""
    with patch("foxhole_stockpiles.gui.app.QApplication") as mock_app_class:
        mock_app = MagicMock()
        mock_app_class.return_value = mock_app
        mock_app.exec.return_value = 0

        with patch("foxhole_stockpiles.gui.app.MainWindow") as mock_window_class:
            mock_window = MagicMock()
            mock_window_class.return_value = mock_window

            with patch("sys.exit") as mock_exit:
                launch_gui()

                # Should start event loop
                mock_app.exec.assert_called_once()

                # Should exit with return code from exec
                mock_exit.assert_called_once_with(0)


def test_launch_gui_exits_with_correct_code() -> None:
    """Test launch_gui exits with correct code from event loop."""
    with patch("foxhole_stockpiles.gui.app.QApplication") as mock_app_class:
        mock_app = MagicMock()
        mock_app_class.return_value = mock_app
        mock_app.exec.return_value = 42  # Non-zero exit code

        with patch("foxhole_stockpiles.gui.app.MainWindow") as mock_window_class:
            mock_window = MagicMock()
            mock_window_class.return_value = mock_window

            with patch("sys.exit") as mock_exit:
                launch_gui()

                # Should exit with code from exec
                mock_exit.assert_called_once_with(42)


def test_launch_gui_sets_application_name() -> None:
    """Test launch_gui sets correct application name."""
    with patch("foxhole_stockpiles.gui.app.QApplication") as mock_app_class:
        mock_app = MagicMock()
        mock_app_class.return_value = mock_app
        mock_app.exec.return_value = 0

        with patch("foxhole_stockpiles.gui.app.MainWindow"):
            with patch("sys.exit"):
                launch_gui()

                mock_app.setApplicationName.assert_called_once_with("FS")


def test_launch_gui_sets_organization_name() -> None:
    """Test launch_gui sets correct organization name."""
    with patch("foxhole_stockpiles.gui.app.QApplication") as mock_app_class:
        mock_app = MagicMock()
        mock_app_class.return_value = mock_app
        mock_app.exec.return_value = 0

        with patch("foxhole_stockpiles.gui.app.MainWindow"):
            with patch("sys.exit"):
                launch_gui()

                mock_app.setOrganizationName.assert_called_once_with("FS")


def test_launch_gui_sets_application_version() -> None:
    """Test launch_gui sets application version."""
    with patch("foxhole_stockpiles.gui.app.QApplication") as mock_app_class:
        mock_app = MagicMock()
        mock_app_class.return_value = mock_app
        mock_app.exec.return_value = 0

        with patch("foxhole_stockpiles.gui.app.MainWindow"):
            with patch("sys.exit"):
                with patch("foxhole_stockpiles.gui.app.__version__", "1.2.3"):
                    launch_gui()

                    mock_app.setApplicationVersion.assert_called_once_with("1.2.3")


def test_launch_gui_uses_sys_argv() -> None:
    """Test launch_gui passes sys.argv to QApplication."""
    with patch("foxhole_stockpiles.gui.app.QApplication") as mock_app_class:
        mock_app = MagicMock()
        mock_app_class.return_value = mock_app
        mock_app.exec.return_value = 0

        with patch("foxhole_stockpiles.gui.app.MainWindow"):
            with patch("sys.exit"):
                with patch("sys.argv", ["test", "arg1", "arg2"]):
                    launch_gui()

                    # Should pass sys.argv to QApplication
                    args = mock_app_class.call_args[0][0]
                    assert args == ["test", "arg1", "arg2"]


def test_launch_gui_window_shown_before_exec() -> None:
    """Test window is shown before starting event loop."""
    with patch("foxhole_stockpiles.gui.app.QApplication") as mock_app_class:
        mock_app = MagicMock()
        mock_app_class.return_value = mock_app

        call_order = []

        def track_show() -> None:
            call_order.append("show")

        def track_exec() -> int:
            call_order.append("exec")
            return 0

        mock_app.exec.side_effect = track_exec

        with patch("foxhole_stockpiles.gui.app.MainWindow") as mock_window_class:
            mock_window = MagicMock()
            mock_window.show.side_effect = track_show
            mock_window_class.return_value = mock_window

            with patch("sys.exit"):
                launch_gui()

                # Window should be shown before exec
                assert call_order == ["show", "exec"]


def test_load_language_from_settings_default() -> None:
    """Test _load_language_from_settings returns configured language."""
    with patch("foxhole_stockpiles.gui.app.AppSettings") as mock_settings_class:
        mock_settings = MagicMock()
        mock_settings.gui.language = "fr"
        mock_settings_class.return_value = mock_settings

        result = _load_language_from_settings()

        assert result == "fr"


def test_load_language_from_settings_error_fallback() -> None:
    """Test _load_language_from_settings falls back to 'en' on error."""
    with patch("foxhole_stockpiles.gui.app.AppSettings") as mock_settings_class:
        mock_settings_class.side_effect = Exception("Config error")

        result = _load_language_from_settings()

        assert result == "en"
