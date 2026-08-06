from pathlib import Path
import ast
import compileall
import sys

root = Path(__file__).resolve().parent
files = list((root / "app").rglob("*.py"))
for path in files:
    ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
if not compileall.compile_dir(str(root / "app"), quiet=1):
    raise SystemExit(1)
print(f"PREVALIDACION CORRECTA | ARCHIVOS PYTHON: {len(files)}")
