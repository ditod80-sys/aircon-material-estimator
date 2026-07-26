"""Main application window for the Phase 0 CAD inspection workflow."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QProgressBar,
    QVBoxLayout,
    QWidget,
    QFileDialog,
)

from database.settings import APP_NAME, VERSION
from reader.dwg_reader import DrawingReadError, DWGReader


class MainWindow(QMainWindow):
    """Provide file selection and a simple DXF/DWG entity summary."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {VERSION}")
        self.setMinimumSize(760, 520)
        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        central_widget = QWidget(self)
        layout = QVBoxLayout(central_widget)

        layout.addWidget(QLabel("Drawing file (.dwg or .dxf):"))

        file_layout = QHBoxLayout()
        self.drawing_edit = QLineEdit()
        self.drawing_edit.setPlaceholderText("Select a DWG or DXF drawing file")
        self.select_button = QPushButton("Select file...")
        file_layout.addWidget(self.drawing_edit)
        file_layout.addWidget(self.select_button)
        layout.addLayout(file_layout)

        self.analyze_button = QPushButton("Analyze drawing")
        self.analyze_button.setDefault(True)
        layout.addWidget(self.analyze_button)

        layout.addWidget(QLabel("Progress:"))
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        layout.addWidget(QLabel("Analysis log:"))
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log, stretch=1)

        self.setCentralWidget(central_widget)
        self.statusBar().showMessage("Ready")

    def _connect_signals(self) -> None:
        self.select_button.clicked.connect(self.select_drawing)
        self.analyze_button.clicked.connect(self.analyze_drawing)
        self.drawing_edit.returnPressed.connect(self.analyze_drawing)

    def select_drawing(self) -> None:
        """Let the user choose a supported drawing file."""
        selected_file, _ = QFileDialog.getOpenFileName(
            self,
            "Select drawing",
            str(Path.home()),
            "CAD drawings (*.dwg *.dxf);;DWG drawings (*.dwg);;DXF drawings (*.dxf)",
        )
        if selected_file:
            self.drawing_edit.setText(selected_file)
            self._append_log(f"Selected: {selected_file}")

    def analyze_drawing(self) -> None:
        """Read the selected drawing and display entity-type counts."""
        drawing_path = Path(self.drawing_edit.text().strip())
        self.log.clear()
        self.progress.setValue(0)

        if not self.drawing_edit.text().strip():
            self._show_error("Select a DWG or DXF drawing before starting analysis.")
            return

        self._set_busy(True)
        try:
            self.progress.setValue(10)
            self._append_log(f"Starting analysis: {drawing_path}")

            reader = DWGReader()
            self.progress.setValue(30)
            entities = reader.read(drawing_path)
            self.progress.setValue(80)

            counts = Counter(entity.dxftype() for entity in entities)
            self._append_log("")
            self._append_log("========== Analysis result ==========")
            self._append_log(f"Total modelspace entities: {len(entities)}")
            for entity_type, count in sorted(counts.items()):
                self._append_log(f"{entity_type:<15} : {count}")
            self._append_log("=====================================")
            self.progress.setValue(100)
            self.statusBar().showMessage("Analysis complete")
        except DrawingReadError as error:
            self.progress.setValue(0)
            self._show_error(str(error))
        except Exception as error:  # Preserve an actionable UI even for unexpected defects.
            self.progress.setValue(0)
            self._show_error(f"Unexpected analysis error: {error}")
        finally:
            self._set_busy(False)

    def _set_busy(self, busy: bool) -> None:
        self.select_button.setEnabled(not busy)
        self.analyze_button.setEnabled(not busy)
        self.drawing_edit.setEnabled(not busy)
        self.setCursor(Qt.CursorShape.WaitCursor if busy else Qt.CursorShape.ArrowCursor)

    def _show_error(self, message: str) -> None:
        self._append_log(f"ERROR: {message}")
        self.statusBar().showMessage("Analysis failed")
        QMessageBox.critical(self, APP_NAME, message)

    def _append_log(self, message: str) -> None:
        self.log.appendPlainText(message)
