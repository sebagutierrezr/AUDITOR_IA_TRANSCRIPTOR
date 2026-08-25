from __future__ import annotations

import argparse
import os
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    args = parser.parse_args()

    model = Path(args.model).resolve()
    for name in (
        "hyperparams.yaml",
        "embedding_model.ckpt",
        "mean_var_norm_emb.ckpt",
        "classifier.ckpt",
        "label_encoder.txt",
    ):
        if not (model / name).is_file():
            raise RuntimeError(f"ECAPA incompleto: falta {name}")

    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

    import torch

    from app.services.speechbrain_compat import (
        patch_speechbrain_lazy_import,
    )

    patch_speechbrain_lazy_import()

    from speechbrain.inference.speaker import EncoderClassifier

    classifier = EncoderClassifier.from_hparams(
        source=str(model),
        savedir=str(model),
        run_opts={"device": "cpu"},
        overrides={"pretrained_path": str(model).replace("\\", "/")},
    )
    sample = torch.zeros(1, 16000)
    sample[:, 2000:12000] = 0.01
    embedding = classifier.encode_batch(sample)
    if embedding.numel() <= 0:
        raise RuntimeError("ECAPA no generó embedding.")
    print("ECAPA LOCAL: OK", tuple(embedding.shape))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
