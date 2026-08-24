from __future__ import annotations

import os
from pathlib import Path


def _self_test() -> int:
    try:
        import PySide6
        import openai
        import docx
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance() or QApplication([])
        app.quit()
        Path("runtime_self_test_ok.txt").write_text(
            "\n".join(
                [
                    f"PySide6={PySide6.__version__}",
                    f"OpenAI={getattr(openai, '__version__', 'OK')}",
                    "python-docx=OK",
                    "UI=OK",
                ]
            ),
            encoding="utf-8",
        )
        return 0
    except Exception as exc:
        try:
            Path("runtime_self_test_error.txt").write_text(
                f"{type(exc).__name__}: {exc}", encoding="utf-8"
            )
        except Exception:
            pass
        return 91


if os.environ.get("AUDITOR_IA_SELF_TEST") == "1":
    raise SystemExit(_self_test())

from app.bootstrap import run_app

if __name__ == "__main__":
    raise SystemExit(run_app())
