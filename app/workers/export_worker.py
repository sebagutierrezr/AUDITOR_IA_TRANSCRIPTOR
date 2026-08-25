from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from app.services.export_service import ExportService


class ExportWorker(QObject):
    completed = Signal(str)
    failed = Signal(str)
    finished = Signal()

    def __init__(
        self,
        destination: Path,
        text: str,
        source_name: str,
        export_type: str,
    ) -> None:
        super().__init__()
        self.destination = destination
        self.text = text
        self.source_name = source_name
        self.export_type = export_type
        self.service = ExportService()

    @Slot()
    def run(self) -> None:
        try:
            if self.export_type == "txt":
                self.service.export_txt(
                    self.destination,
                    self.text,
                )
            elif self.export_type == "docx":
                self.service.export_docx(
                    self.destination,
                    self.text,
                    self.source_name,
                )
            else:
                raise ValueError(
                    "TIPO DE EXPORTACIÓN NO COMPATIBLE."
                )

            self.completed.emit(
                str(self.destination)
            )

        except Exception as exc:
            detail = str(exc).strip() or type(exc).__name__
            self.failed.emit(
                f"{type(exc).__name__}: {detail}"
            )

        finally:
            self.finished.emit()
