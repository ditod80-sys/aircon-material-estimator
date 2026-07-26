"""Application entry point for the Phase 0 desktop shell."""

from __future__ import annotations

import sys
import traceback

from PySide6.QtWidgets import QApplication, QMessageBox


def main() -> int:
    """Create and run the desktop application."""
    app = QApplication(sys.argv)
    app_name = "Aircon Material Estimator"

    try:
        from database.settings import APP_NAME
        from ui.main_window import MainWindow

        app_name = APP_NAME
        app.setApplicationName(app_name)
        window = MainWindow()
        window.show()
        return app.exec()
    except Exception as error:  # Last-resort startup protection.
        traceback.print_exc()
        QMessageBox.critical(
            None,
            app_name,
            f"The application could not start.\n\n{error}",
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
