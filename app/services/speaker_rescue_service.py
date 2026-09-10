from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.models.conversation import Conversation
from app.services.paths_service import AppPaths


@dataclass(frozen=True)
class RescueTurn:
    start: float
    end: float
    speaker: str

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


class SpeakerRescueService:
    """
    Segunda capa acústica local.

    Community-1 sigue siendo la primera capa. Si esa salida colapsa en un
    hablante, deja al segundo casi sin tiempo o produce una separación dudosa,
    ECAPA-TDNN vuelve a comparar huellas vocales y fuerza exactamente 2 grupos.
    """

    MODEL_FOLDER = "speechbrain-ecapa"
    _classifier = None

    def __init__(self) -> None:
        self._paths = AppPaths()
        self._logger = logging.getLogger(__name__)

    @property
    def model_path(self) -> Path:
        return self._paths.models / self.MODEL_FOLDER

    def is_ready(self) -> bool:
        required = (
            "hyperparams.yaml",
            "embedding_model.ckpt",
            "mean_var_norm_emb.ckpt",
            "classifier.ckpt",
            "label_encoder.txt",
        )
        return all(
            (self.model_path / name).is_file()
            and (self.model_path / name).stat().st_size > 0
            for name in required
        )

    def recover_two_speakers(
        self,
        conversation: Conversation,
        audio_path: Path,
        progress_callback=None,
    ) -> list[RescueTurn]:
        if not self.is_ready():
            raise RuntimeError(
                "EL MODELO ECAPA DE RESCATE NO ESTÁ INSTALADO O ESTÁ INCOMPLETO."
            )

        chunks = self._candidate_chunks(conversation)
        if len(chunks) < 2:
            raise RuntimeError(
                "NO HAY SUFICIENTES INTERVENCIONES PARA RECUPERAR DOS VOCES."
            )

        if progress_callback:
            progress_callback(94, "SEGUNDA CAPA: ANALIZANDO HUELLAS DE VOZ...")

        waveform, sample_rate = self._load_audio(audio_path)
        classifier = self._load_classifier()

        vectors: list[np.ndarray] = []
        accepted: list[tuple[float, float]] = []

        for index, (start, end) in enumerate(chunks):
            clip = self._crop(waveform, sample_rate, start, end)
            if clip is None:
                continue

            vector = self._embedding(classifier, clip)
            if vector is None:
                continue

            vectors.append(vector)
            accepted.append((start, end))

            if progress_callback:
                ratio = (index + 1) / max(1, len(chunks))
                progress_callback(
                    94 + min(3, int(ratio * 3)),
                    f"SEGUNDA CAPA: COMPARANDO VOCES... {int(ratio * 100)} %",
                )

        if len(vectors) < 2:
            raise RuntimeError("NO FUE POSIBLE EXTRAER DOS HUELLAS VOCALES.")

        matrix = np.vstack(vectors)
        labels = self._cluster_two(matrix)
        unique = sorted(set(int(v) for v in labels))
        if len(unique) != 2:
            raise RuntimeError("ECAPA NO PUDO ESTABLECER DOS GRUPOS DE VOZ.")

        turns = [
            RescueTurn(
                start=float(start),
                end=float(end),
                speaker=f"ECAPA_{int(label)}",
            )
            for (start, end), label in zip(accepted, labels)
        ]
        return self._merge_adjacent(turns)

    def _load_classifier(self):
        if self.__class__._classifier is not None:
            return self.__class__._classifier

        import os
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

        from app.services.speechbrain_compat import (
            patch_speechbrain_lazy_import,
        )

        patch_speechbrain_lazy_import()

        from speechbrain.inference.speaker import EncoderClassifier

        classifier = EncoderClassifier.from_hparams(
            source=str(self.model_path),
            savedir=str(self.model_path),
            run_opts={"device": "cpu"},
            overrides={"pretrained_path": str(self.model_path).replace("\\", "/")},
        )
        self.__class__._classifier = classifier
        return classifier

    @staticmethod
    def _load_audio(audio_path: Path):
        import torchaudio
        waveform, sample_rate = torchaudio.load(str(audio_path))
        if waveform.ndim == 2 and waveform.shape[0] > 1:
            waveform = waveform.mean(dim=0, keepdim=True)
        return waveform, int(sample_rate)

    @staticmethod
    def _crop(waveform, sample_rate: int, start: float, end: float):
        import torch

        start = max(0.0, float(start))
        end = max(start, float(end))
        if end - start < 0.15:
            return None

        a = max(0, int(start * sample_rate))
        b = min(waveform.shape[-1], int(end * sample_rate))
        if b <= a:
            return None

        clip = waveform[:, a:b]

        # Para respuestas muy cortas ("sí", "seis", etc.) repetimos la misma
        # muestra en lugar de añadir audio vecino que podría ser del otro hablante.
        minimum = int(sample_rate * 0.95)
        if clip.shape[-1] < minimum:
            repeats = int(np.ceil(minimum / max(1, clip.shape[-1])))
            clip = clip.repeat(1, repeats)[:, :minimum]

        # Evita fragmentos excesivamente largos en el embedding.
        maximum = int(sample_rate * 5.0)
        if clip.shape[-1] > maximum:
            clip = clip[:, :maximum]

        return clip

    @staticmethod
    def _embedding(classifier, clip):
        import torch
        with torch.inference_mode():
            embedding = classifier.encode_batch(clip)
        vector = embedding.detach().cpu().numpy().reshape(-1).astype(np.float32)
        norm = float(np.linalg.norm(vector))
        if norm <= 1e-8:
            return None
        return vector / norm

    @staticmethod
    def _cluster_two(matrix: np.ndarray) -> np.ndarray:
        """Separa embeddings en dos grupos sin depender de scikit-learn.

        Los embeddings ECAPA ya se normalizan antes de llegar aqui. Aun asi
        normalizamos de forma defensiva y usamos un k-means esferico de dos
        centros (similitud coseno). Esto evita instalar ``scikit-learn`` solo
        para esta operacion y mantiene el runtime coherente con el .spec, que
        deliberadamente no empaqueta esa libreria pesada.
        """
        values = np.asarray(matrix, dtype=np.float32)
        if values.ndim != 2 or values.shape[0] < 2:
            raise ValueError("SE REQUIEREN AL MENOS DOS EMBEDDINGS DE VOZ.")
        if values.shape[1] < 1:
            raise ValueError("LOS EMBEDDINGS DE VOZ ESTAN VACIOS.")
        if not np.isfinite(values).all():
            raise ValueError("LOS EMBEDDINGS DE VOZ CONTIENEN VALORES INVALIDOS.")

        count = values.shape[0]
        if count == 2:
            return np.array([0, 1], dtype=np.int32)

        norms = np.linalg.norm(values, axis=1, keepdims=True)
        safe = np.where(norms > 1e-8, norms, 1.0)
        unit = values / safe

        # Semillas deterministas: las dos huellas con menor similitud coseno.
        similarity = unit @ unit.T
        np.fill_diagonal(similarity, np.inf)
        flat_index = int(np.argmin(similarity))
        seed_a, seed_b = np.unravel_index(flat_index, similarity.shape)
        if seed_a == seed_b:
            seed_a, seed_b = 0, count - 1

        centers = np.vstack((unit[seed_a], unit[seed_b])).astype(np.float32)
        labels = np.full(count, -1, dtype=np.int32)

        for _ in range(50):
            scores = unit @ centers.T
            updated = np.argmax(scores, axis=1).astype(np.int32)

            # Nunca permitir un cluster vacio. Si ocurre, se mueve al segundo
            # grupo la muestra mas ambigua del grupo dominante.
            for cluster_id in (0, 1):
                if np.any(updated == cluster_id):
                    continue
                other = 1 - cluster_id
                members = np.where(updated == other)[0]
                if members.size <= 1:
                    continue
                margins = np.abs(scores[members, 0] - scores[members, 1])
                moved = int(members[int(np.argmin(margins))])
                updated[moved] = cluster_id

            if np.array_equal(updated, labels):
                break
            labels = updated

            new_centers = []
            for cluster_id in (0, 1):
                members = unit[labels == cluster_id]
                if members.size == 0:
                    new_centers.append(centers[cluster_id])
                    continue
                center = members.mean(axis=0)
                norm = float(np.linalg.norm(center))
                if norm > 1e-8:
                    center = center / norm
                new_centers.append(center)
            centers = np.vstack(new_centers).astype(np.float32)

        if len(set(int(v) for v in labels.tolist())) != 2:
            raise RuntimeError("NO FUE POSIBLE FORMAR DOS GRUPOS DE VOZ.")

        # Canoniza los IDs segun primera aparicion para resultados reproducibles.
        first_label = int(labels[0])
        if first_label != 0:
            labels = (1 - labels).astype(np.int32)
        return labels

    @staticmethod
    def _candidate_chunks(conversation: Conversation) -> list[tuple[float, float]]:
        """Crea fragmentos acústicamente más puros desde timestamps de palabra."""
        chunks: list[tuple[float, float]] = []

        for segment in conversation.segments:
            words = list(getattr(segment, "words", None) or [])
            if not words:
                if float(segment.end) - float(segment.start) >= 0.15:
                    chunks.append((float(segment.start), float(segment.end)))
                continue

            current_start = None
            current_end = None
            previous_text = ""

            for word in words:
                start = float(word.get("start", segment.start))
                end = float(word.get("end", segment.end))
                text = str(word.get("text", "") or "").strip()

                if current_start is None:
                    current_start, current_end = start, end
                    previous_text = text
                    continue

                gap = max(0.0, start - current_end)
                duration = current_end - current_start
                sentence_boundary = previous_text.endswith((".", "?", "!", ":", ";"))

                if gap >= 0.34 or duration >= 3.8 or (sentence_boundary and duration >= 0.75):
                    if current_end - current_start >= 0.15:
                        chunks.append((current_start, current_end))
                    current_start, current_end = start, end
                else:
                    current_end = end

                previous_text = text

            if current_start is not None and current_end is not None:
                if current_end - current_start >= 0.15:
                    chunks.append((current_start, current_end))

        # El rescate no debe convertir una entrevista larga en cientos de pasadas.
        if len(chunks) > 90:
            step = max(1, len(chunks) // 90)
            chunks = chunks[::step][:90]

        return chunks

    @staticmethod
    def _merge_adjacent(turns: list[RescueTurn]) -> list[RescueTurn]:
        if not turns:
            return []
        ordered = sorted(turns, key=lambda row: (row.start, row.end))
        merged = [ordered[0]]
        for item in ordered[1:]:
            previous = merged[-1]
            if item.speaker == previous.speaker and item.start - previous.end <= 0.42:
                merged[-1] = RescueTurn(
                    start=previous.start,
                    end=max(previous.end, item.end),
                    speaker=previous.speaker,
                )
            else:
                merged.append(item)
        return merged
