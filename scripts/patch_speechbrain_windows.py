from __future__ import annotations

import argparse
import importlib.util
import re
from pathlib import Path

NEW_EXPRESSION = 'os.path.basename(importer_frame.filename) == "inspect.py"'


def locate_importutils() -> Path:
    spec = importlib.util.find_spec("speechbrain.utils.importutils")
    if spec is None or not spec.origin:
        raise RuntimeError("No se encontró speechbrain.utils.importutils.")
    path = Path(spec.origin).resolve()
    if not path.is_file():
        raise RuntimeError(f"speechbrain importutils no existe: {path}")
    return path


def patch_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")

    if NEW_EXPRESSION in text:
        print("SPEECHBRAIN WINDOWS PATCH: YA APLICADO")
        return False

    updated, count = re.subn(
        r'importer_frame\.filename\.endswith\(\s*["\']/inspect\.py["\']\s*\)',
        NEW_EXPRESSION,
        text,
        count=1,
        flags=re.MULTILINE,
    )

    if count != 1:
        raise RuntimeError(
            "No se encontró la condición defectuosa de SpeechBrain para inspect.py."
        )

    path.write_text(updated, encoding="utf-8")

    verify = path.read_text(encoding="utf-8")
    if NEW_EXPRESSION not in verify:
        raise RuntimeError("El parche de SpeechBrain no quedó aplicado.")

    print("SPEECHBRAIN WINDOWS PATCH: APLICADO")
    print(path)
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default="")
    args = parser.parse_args()

    path = Path(args.file).resolve() if args.file else locate_importutils()
    patch_file(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
