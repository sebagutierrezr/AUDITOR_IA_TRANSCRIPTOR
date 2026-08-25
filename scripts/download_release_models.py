from __future__ import annotations

import os
import shutil
from pathlib import Path

from huggingface_hub import snapshot_download

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "models"

WHISPER_REPO = "Systran/faster-whisper-small"
WHISPER_FOLDER = MODELS / "small"
COMMUNITY_REPO = "pyannote/speaker-diarization-community-1"
COMMUNITY_FOLDER = MODELS / "pyannote-community-1"
ECAPA_REPO = "speechbrain/spkrec-ecapa-voxceleb"
ECAPA_FOLDER = MODELS / "speechbrain-ecapa"


def ready(path: Path, required: tuple[str, ...]) -> bool:
    return all(
        (path / name).is_file() and (path / name).stat().st_size > 0
        for name in required
    )


def clean_cache(path: Path) -> None:
    cache = path / ".cache"
    if cache.exists():
        shutil.rmtree(cache, ignore_errors=True)


def download(repo_id: str, destination: Path, *, token=None, allow_patterns=None):
    if destination.exists():
        shutil.rmtree(destination)
    snapshot_download(
        repo_id=repo_id,
        token=token,
        local_dir=str(destination),
        allow_patterns=allow_patterns,
    )
    clean_cache(destination)


def main() -> None:
    MODELS.mkdir(parents=True, exist_ok=True)

    whisper_required = ("model.bin", "config.json", "tokenizer.json")
    if not ready(WHISPER_FOLDER, whisper_required):
        download(
            WHISPER_REPO,
            WHISPER_FOLDER,
            allow_patterns=[
                "model.bin",
                "config.json",
                "tokenizer.json",
                "vocabulary.*",
                "preprocessor_config.json",
            ],
        )
    if not ready(WHISPER_FOLDER, whisper_required):
        raise RuntimeError("FASTER-WHISPER SMALL INCOMPLETO.")
    print("FASTER-WHISPER SMALL: LISTO")

    token = os.environ.get("HF_TOKEN", "").strip()
    if not token:
        raise RuntimeError("FALTA HF_TOKEN PARA DESCARGAR COMMUNITY-1 EN EL BUILD.")
    if not ready(COMMUNITY_FOLDER, ("config.yaml",)):
        download(COMMUNITY_REPO, COMMUNITY_FOLDER, token=token)
    if not ready(COMMUNITY_FOLDER, ("config.yaml",)):
        raise RuntimeError("COMMUNITY-1 INCOMPLETO.")
    print("COMMUNITY-1: LISTO")

    ecapa_required = (
        "hyperparams.yaml",
        "embedding_model.ckpt",
        "mean_var_norm_emb.ckpt",
        "classifier.ckpt",
        "label_encoder.txt",
    )
    if not ready(ECAPA_FOLDER, ecapa_required):
        download(
            ECAPA_REPO,
            ECAPA_FOLDER,
            allow_patterns=[
                "hyperparams.yaml",
                "embedding_model.ckpt",
                "mean_var_norm_emb.ckpt",
                "classifier.ckpt",
                "label_encoder.txt",
                "config.json",
            ],
        )
    if not ready(ECAPA_FOLDER, ecapa_required):
        raise RuntimeError("ECAPA INCOMPLETO.")
    print("ECAPA RESCUE: LISTO")


if __name__ == "__main__":
    main()
