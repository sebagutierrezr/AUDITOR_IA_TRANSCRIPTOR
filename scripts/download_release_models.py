from __future__ import annotations

import shutil
from pathlib import Path

from huggingface_hub import snapshot_download


ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "models"

RELEASE_MODELS = {
    "base": "Systran/faster-whisper-base",
    "small": "Systran/faster-whisper-small",
}


def model_ready(path: Path) -> bool:
    required = (
        "model.bin",
        "config.json",
        "tokenizer.json",
    )
    return all((path / name).is_file() for name in required)


def main() -> None:
    MODELS.mkdir(parents=True, exist_ok=True)

    for name, repo_id in RELEASE_MODELS.items():
        destination = MODELS / name

        if model_ready(destination):
            print(f"MODELO {name.upper()}: YA DISPONIBLE")
            continue

        if destination.exists():
            shutil.rmtree(destination)

        destination.mkdir(parents=True, exist_ok=True)
        print(f"DESCARGANDO {repo_id}...")

        snapshot_download(
            repo_id=repo_id,
            local_dir=str(destination),
            allow_patterns=[
                "model.bin",
                "config.json",
                "tokenizer.json",
                "vocabulary.*",
                "preprocessor_config.json",
            ],
        )

        cache = destination / ".cache"
        if cache.exists():
            shutil.rmtree(cache, ignore_errors=True)

        if not model_ready(destination):
            raise RuntimeError(
                f"EL MODELO {name.upper()} QUEDÓ INCOMPLETO."
            )

        print(f"MODELO {name.upper()}: LISTO")

    print("MODELOS DE DISTRIBUCIÓN VERIFICADOS.")


if __name__ == "__main__":
    main()
