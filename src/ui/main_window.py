"""Main application window for the Phase 0 CAD inspection workflow."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QFileDialog,
)

from database.catalog_builder import CatalogBuilderError, SamsungCatalogCandidateBuilder
from database.settings import APP_NAME, OUTPUT_DIR, VERSION
from engine.block_statistics import BlockStatisticsBuilder
from engine.indoor_unit_recognizer import IndoorUnitRecognizer
from excel.exporter import (
    BlockStatisticsCsvExportError,
    BlockStatisticsCsvExporter,
    InsertCsvExportError,
    InsertCsvExporter,
    IndoorUnitsCsvExportError,
    IndoorUnitsCsvExporter,
)
from database.catalog_loader import (
    CatalogLoadError,
    CatalogSaveError,
    IndoorUnitCatalog,
    SamsungCatalogRepository,
)
from engine.model import IndoorUnitCatalogEntry
from reader.dwg_reader import DrawingReadError, DWGReader


class MainWindow(QMainWindow):
    """Provide catalog-driven indoor-unit recognition over CAD INSERT blocks."""

    def __init__(self) -> None:
        super().__init__()
        self.current_inserts: list[object] = []
        self.setWindowTitle(f"{APP_NAME} {VERSION}")
        self.setMinimumSize(980, 720)
        self.resize(1200, 800)
        self.move(100, 100)
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

        self.analyze_button = QPushButton("Inspect INSERT blocks")
        self.analyze_button.setDefault(True)
        layout.addWidget(self.analyze_button)

        self.build_catalog_button = QPushButton("Build Samsung catalog candidates")
        layout.addWidget(self.build_catalog_button)

        layout.addWidget(QLabel("Unknown INSERT blocks (edit complete rows, then save):"))
        self.unknown_table = QTableWidget(0, 7)
        self.unknown_table.setHorizontalHeaderLabels(
            ("Block Name", "Count", "Layer", "Suggested Type", "Suggested Capacity", "Manufacturer", "Model")
        )
        self.unknown_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.unknown_table.setMinimumHeight(220)
        layout.addWidget(self.unknown_table)

        self.save_catalog_button = QPushButton("Save to Samsung Catalog")
        self.save_catalog_button.setEnabled(False)
        layout.addWidget(self.save_catalog_button)

        layout.addWidget(QLabel("Progress:"))
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        layout.addWidget(QLabel("Inspection log:"))
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log, stretch=1)

        self.setCentralWidget(central_widget)
        self.statusBar().showMessage("Ready")

    def _connect_signals(self) -> None:
        self.select_button.clicked.connect(self.select_drawing)
        self.analyze_button.clicked.connect(self.analyze_drawing)
        self.build_catalog_button.clicked.connect(self.build_catalog_candidates)
        self.save_catalog_button.clicked.connect(self.save_to_samsung_catalog)
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
        """Inspect INSERT blocks and export their neutral CAD metadata."""
        drawing_path = Path(self.drawing_edit.text().strip())
        self.log.clear()
        self.progress.setValue(0)

        if not self.drawing_edit.text().strip():
            self._show_error("Select a DWG or DXF drawing before starting analysis.")
            return

        self._set_busy(True)
        try:
            self.progress.setValue(10)
            self._append_log(f"Starting INSERT inspection: {drawing_path}")

            reader = DWGReader()
            self.progress.setValue(30)
            inserts = reader.read_inserts(drawing_path)
            self.current_inserts = inserts
            self.progress.setValue(55)

            inserts_csv_path = InsertCsvExporter().export(drawing_path, inserts)
            statistics = BlockStatisticsBuilder().build(inserts)
            self.progress.setValue(75)

            statistics_csv_path = BlockStatisticsCsvExporter().export(drawing_path, statistics)
            catalog = IndoorUnitCatalog.load_default()
            recognition = IndoorUnitRecognizer(catalog).recognize(inserts)
            indoor_units_csv_path = IndoorUnitsCsvExporter().export(drawing_path, recognition.indoor_units)
            self.progress.setValue(90)

            self._append_log("")
            self._append_log("========== INSERT inspection ==========")
            self._append_log(f"Total INSERT entities: {len(inserts)}")
            self._append_log(f"INSERT CSV export: {inserts_csv_path}")
            self._append_log(f"Block statistics CSV export: {statistics_csv_path}")
            self._append_log(f"Indoor units CSV export: {indoor_units_csv_path}")
            self._append_log("")
            self._append_log("First 100 INSERT blocks:")
            if not inserts:
                self._append_log("(No INSERT entities found.)")
            for index, insert in enumerate(inserts[:100], start=1):
                scale = f"({insert.scale_x:g}, {insert.scale_y:g}, {insert.scale_z:g})"
                self._append_log(
                    f"{index:>3}. block={insert.block_name} | layer={insert.layer} | "
                    f"point=({insert.x:g}, {insert.y:g}) | scale={scale} | rotation={insert.rotation:g}"
                )
            if len(inserts) > 100:
                self._append_log(f"... {len(inserts) - 100} additional INSERT blocks exported to CSV.")
            self._append_log("")
            self._append_log("Top 30 block names by count:")
            if not statistics:
                self._append_log("(No block statistics available.)")
            for index, statistic in enumerate(statistics[:30], start=1):
                layers = ", ".join(statistic.layers)
                self._append_log(
                    f"{index:>3}. block={statistic.block_name} | count={statistic.count} | layers={layers}"
                )
            if len(statistics) > 30:
                self._append_log(f"... {len(statistics) - 30} additional block names exported to CSV.")
            self._append_log("")
            self._append_log("========== Indoor Unit Recognition ==========")
            self._append_log(f"Catalog Entries: {catalog.entry_count}")
            self._append_log(f"Indoor Units Found: {recognition.indoor_unit_count}")
            self._append_log(f"Recognized Blocks: {recognition.indoor_unit_count}")
            self._append_log(
                "Unknown Blocks: "
                f"{recognition.unknown_insert_count} INSERT(s) across {len(recognition.unknown_blocks)} block name(s)"
            )
            self._append_log(f"Recognition Rate: {recognition.recognition_rate:.1f}%")
            self._append_log("Unknown block names:")
            if not recognition.unknown_blocks:
                self._append_log("(None)")
            for unknown_block in recognition.unknown_blocks[:30]:
                layers = ", ".join(unknown_block.layers)
                self._append_log(
                    f"- {unknown_block.block_name} | count={unknown_block.count} | layers={layers}"
                )
            if len(recognition.unknown_blocks) > 30:
                self._append_log(
                    f"... {len(recognition.unknown_blocks) - 30} additional unknown block names not shown."
                )
            self._populate_unknown_blocks(recognition)
            self._append_log("=====================================")
            self.progress.setValue(100)
            self.statusBar().showMessage("INSERT inspection complete")
        except DrawingReadError as error:
            self.progress.setValue(0)
            self._show_error(str(error))
        except InsertCsvExportError as error:
            self.progress.setValue(0)
            self._show_error(str(error))
        except BlockStatisticsCsvExportError as error:
            self.progress.setValue(0)
            self._show_error(str(error))
        except (CatalogLoadError, IndoorUnitsCsvExportError) as error:
            self.progress.setValue(0)
            self._show_error(str(error))
        except Exception as error:  # Preserve an actionable UI even for unexpected defects.
            self.progress.setValue(0)
            self._show_error(f"Unexpected analysis error: {error}")
        finally:
            self._set_busy(False)

    def save_to_samsung_catalog(self) -> None:
        """Append complete user-reviewed rows and refresh current recognition."""
        entries, incomplete_block_names = self._catalog_entries_from_table()
        if incomplete_block_names:
            self._show_error(
                "Complete Manufacturer, Suggested Type, Suggested Capacity, and Model before saving: "
                + ", ".join(incomplete_block_names)
            )
            return
        if not entries:
            self._show_error("Enter Type, Capacity, and Model for at least one unknown block before saving.")
            return
        if not self.current_inserts:
            self._show_error("Run INSERT inspection before saving catalog entries.")
            return

        self._set_busy(True)
        try:
            self.progress.setValue(25)
            saved_count = SamsungCatalogRepository().append(entries)
            self.progress.setValue(60)
            catalog = IndoorUnitCatalog.load_default()
            recognition = IndoorUnitRecognizer(catalog).recognize(self.current_inserts)
            drawing_path = Path(self.drawing_edit.text().strip())
            indoor_units_csv_path = IndoorUnitsCsvExporter().export(drawing_path, recognition.indoor_units)
            self._populate_unknown_blocks(recognition)
            self.progress.setValue(100)
            self._append_log("")
            self._append_log("========== Samsung Catalog Saved ==========")
            self._append_log(f"Entries appended: {saved_count}")
            self._append_log(f"Catalog Entries: {catalog.entry_count}")
            self._append_log(f"Recognized Blocks: {recognition.indoor_unit_count}")
            self._append_log(f"Recognition Rate: {recognition.recognition_rate:.1f}%")
            self._append_log(f"Updated indoor units CSV: {indoor_units_csv_path}")
            self.statusBar().showMessage("Samsung catalog saved and recognition reloaded")
        except (CatalogLoadError, CatalogSaveError, IndoorUnitsCsvExportError) as error:
            self.progress.setValue(0)
            self._show_error(str(error))
        finally:
            self._set_busy(False)

    def build_catalog_candidates(self) -> None:
        """Build a review-only candidate JSON from the existing statistics CSV."""
        drawing_text = self.drawing_edit.text().strip()
        if not drawing_text:
            self._show_error("Select a drawing before building catalog candidates.")
            return

        drawing_path = Path(drawing_text)
        statistics_path = OUTPUT_DIR / f"{drawing_path.stem}_block_statistics.csv"
        self._set_busy(True)
        try:
            self.progress.setValue(20)
            self._append_log("")
            self._append_log(f"Reading block statistics: {statistics_path}")
            builder = SamsungCatalogCandidateBuilder()
            candidates = builder.build_from_statistics(statistics_path)
            self.progress.setValue(70)
            candidate_path = builder.export(candidates)
            self.progress.setValue(100)
            self._append_log("========== Samsung Catalog Candidates ==========")
            self._append_log(f"Candidates generated: {len(candidates)}")
            self._append_log(f"Candidate JSON: {candidate_path}")
            self._append_log("Existing manufacturer catalogs were not modified.")
            self.statusBar().showMessage("Samsung catalog candidates created")
        except CatalogBuilderError as error:
            self.progress.setValue(0)
            self._show_error(str(error))
        finally:
            self._set_busy(False)

    def _set_busy(self, busy: bool) -> None:
        self.select_button.setEnabled(not busy)
        self.analyze_button.setEnabled(not busy)
        self.build_catalog_button.setEnabled(not busy)
        self.save_catalog_button.setEnabled(not busy and self.unknown_table.rowCount() > 0)
        self.drawing_edit.setEnabled(not busy)
        self.setCursor(Qt.CursorShape.WaitCursor if busy else Qt.CursorShape.ArrowCursor)

    def _populate_unknown_blocks(self, recognition) -> None:
        """Show every currently unrecognized block with editable catalog fields."""
        self.unknown_table.setRowCount(0)
        suggestion_builder = SamsungCatalogCandidateBuilder()

        for row_index, unknown_block in enumerate(recognition.unknown_blocks):
            suggestion = suggestion_builder.suggest_for_block_name(unknown_block.block_name)
            self.unknown_table.insertRow(row_index)
            self._set_table_item(row_index, 0, unknown_block.block_name, editable=False)
            self._set_table_item(row_index, 1, str(unknown_block.count), editable=False)
            self._set_table_item(row_index, 2, ", ".join(unknown_block.layers), editable=False)
            self._set_table_item(row_index, 3, suggestion.unit_type, editable=True)
            self._set_table_item(row_index, 4, suggestion.capacity, editable=True)
            self._set_table_item(row_index, 5, suggestion.manufacturer, editable=True)
            self._set_table_item(row_index, 6, suggestion.model, editable=True)

        self.save_catalog_button.setEnabled(self.unknown_table.rowCount() > 0)

    def _catalog_entries_from_table(self) -> tuple[list[IndoorUnitCatalogEntry], list[str]]:
        """Return complete edited rows and names of partially edited rows."""
        entries: list[IndoorUnitCatalogEntry] = []
        incomplete_block_names: list[str] = []

        for row_index in range(self.unknown_table.rowCount()):
            block_name = self.unknown_table.item(row_index, 0).text().strip()
            unit_type = self.unknown_table.item(row_index, 3).text().strip()
            capacity = self.unknown_table.item(row_index, 4).text().strip()
            manufacturer = self.unknown_table.item(row_index, 5).text().strip()
            model = self.unknown_table.item(row_index, 6).text().strip()
            if not any((unit_type, capacity, model)):
                continue
            if not all((unit_type, capacity, manufacturer, model)):
                incomplete_block_names.append(block_name)
                continue
            entries.append(
                IndoorUnitCatalogEntry(
                    block_name=block_name,
                    manufacturer=manufacturer,
                    unit_type=unit_type,
                    capacity=capacity,
                    model=model,
                )
            )

        return entries, incomplete_block_names

    def _set_table_item(self, row: int, column: int, value: str, *, editable: bool) -> None:
        item = QTableWidgetItem(value)
        if not editable:
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.unknown_table.setItem(row, column, item)

    def _show_error(self, message: str) -> None:
        self._append_log(f"ERROR: {message}")
        self.statusBar().showMessage("Analysis failed")
        QMessageBox.critical(self, APP_NAME, message)

    def _append_log(self, message: str) -> None:
        self.log.appendPlainText(message)
