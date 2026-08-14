from __future__ import annotations

import os
import sys


def _runtime_self_test() -> int:
    """
    Verifica las dependencias críticas dentro del ejecutable empaquetado.
    No abre la interfaz y no carga los modelos completos.
    """
    try:
        import PySide6
        from PySide6.QtCore import QT_VERSION_STR
        from PySide6.QtWidgets import QApplication

        import av
        import ctranslate2
        import faster_whisper
        import numpy
        import torch
        import pyannote.audio

        # Fuerza también la carga de los bindings Qt principales.
        app = QApplication.instance() or QApplication([])
        _ = QT_VERSION_STR
        _ = PySide6.__version__
        _ = av.__version__
        _ = ctranslate2.__version__
        _ = numpy.__version__
        _ = torch.__version__
        _ = faster_whisper
        _ = pyannote.audio
        app.quit()

        return 0

    except Exception as exc:
        # En builds windowed no hay consola, pero el código de salida
        # permite que GitHub Actions detecte el fallo.
        try:
            Path = __import__("pathlib").Path
            Path("runtime_self_test_error.txt").write_text(
                f"{type(exc).__name__}: {exc}",
                encoding="utf-8",
            )
        except Exception:
            pass

        return 91


if os.environ.get("AUDITOR_IA_SELF_TEST") == "1":
    raise SystemExit(_runtime_self_test())


from app.bootstrap import run_app


if __name__ == "__main__":
    raise SystemExit(run_app())
