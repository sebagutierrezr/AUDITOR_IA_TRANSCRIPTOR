from __future__ import annotations

import os
import shutil
from pathlib import Path

from huggingface_hub import snapshot_download


ROOT = Path(
    os.environ.get(
        "AUDITOR_IA_PROJECT_ROOT",
        str(Path.cwd()),
    )
).resolve()
MODELS = ROOT / "models"

TRANSCRIPTION_MODELS = {
    "base": "Systran/faster-whisper-base",
    "small": "Systran/faster-whisper-small",
}

DIARIZATION_REPO = (
    "pyannote/speaker-diarization-community-1"
)
DIARIZATION_FOLDER = (
    MODELS / "pyannote-community-1"
)


def transcription_ready(path: Path) -> bool:
    required = (
        "model.bin",
        "config.json",
        "tokenizer.json",
    )
    return all(
        (path / name).is_file()
        and (path / name).stat().st_size > 0
        for name in required
    )


def diarization_ready(path: Path) -> bool:
    return (
        (path / "config.yaml").is_file()
        and (path / "config.yaml").stat().st_size > 0
    )


def clean_cache(path: Path) -> None:
    cache = path / ".cache"
    if cache.exists():
        shutil.rmtree(
            cache,
            ignore_errors=True,
        )


def main() -> None:
    MODELS.mkdir(
        parents=True,
        exist_ok=True,
    )

    for name, repo_id in TRANSCRIPTION_MODELS.items():
        destination = MODELS / name

        if not transcription_ready(destination):
            if destination.exists():
                shutil.rmtree(destination)

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
            clean_cache(destination)

        if not transcription_ready(destination):
            raise RuntimeError(
                f"MODELO {name.upper()} INCOMPLETO."
            )

        print(
            f"MODELO {name.upper()}: LISTO"
        )

    token = os.environ.get(
        "HF_TOKEN",
        "",
    ).strip()

    if not token:
        raise RuntimeError(
            "FALTA EL SECRETO HF_TOKEN EN GITHUB. "
            "ACEPTA LAS CONDICIONES DE COMMUNITY-1 "
            "Y CREA UN TOKEN DE HUGGING FACE."
        )

    if not diarization_ready(
        DIARIZATION_FOLDER
    ):
        if DIARIZATION_FOLDER.exists():
            shutil.rmtree(
                DIARIZATION_FOLDER
            )

        snapshot_download(
            repo_id=DIARIZATION_REPO,
            token=token,
            local_dir=str(
                DIARIZATION_FOLDER
            ),
        )
        clean_cache(
            DIARIZATION_FOLDER
        )

    if not diarization_ready(
        DIARIZATION_FOLDER
    ):
        raise RuntimeError(
            "MODELO DE VOCES COMMUNITY-1 INCOMPLETO."
        )

    print(
        "IDENTIFICADOR DE VOCES COMMUNITY-1: LISTO"
    )


if __name__ == "__main__":
    main()
