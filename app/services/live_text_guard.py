from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Sequence

import numpy as np


@dataclass
class TranscriptCandidate:
    label: str
    text: str
    started_at: float
    ended_at: float
    audio_signature: tuple[float, ...] | None = None


class LiveTextGuard:
    """Última barrera contra eco, duplicados y alucinaciones del ASR."""

    @staticmethod
    def normalize_text(text: str) -> str:
        value = unicodedata.normalize("NFKD", str(text or "").casefold())
        value = "".join(char for char in value if not unicodedata.combining(char))
        return " ".join(re.findall(r"[a-z0-9ñ]+", value))

    @staticmethod
    def audio_signature(audio: np.ndarray, sample_rate: int) -> tuple[float, ...] | None:
        """Firma espectral simple, robusta a diferencias de volumen.

        Se usa únicamente para detectar cuando el audio del PC se cuela por el
        micrófono. No identifica personas ni guarda biometría.
        """
        signal = np.asarray(audio, dtype=np.float32).reshape(-1)
        if signal.size < max(1600, int(sample_rate * 0.25)):
            return None
        signal = signal - float(np.mean(signal))
        peak = float(np.max(np.abs(signal)))
        if peak < 1e-5:
            return None
        signal = signal / peak

        target = 8000
        if sample_rate != target:
            size = max(1, int(signal.size * target / float(sample_rate)))
            signal = np.interp(
                np.linspace(0.0, 1.0, size, endpoint=False),
                np.linspace(0.0, 1.0, signal.size, endpoint=False),
                signal,
            ).astype(np.float32)

        frame = 256
        hop = 128
        if signal.size < frame:
            signal = np.pad(signal, (0, frame - signal.size))
        vectors = []
        window = np.hanning(frame).astype(np.float32)
        # Bandas centradas en voz; se omiten DC y ultrabajos.
        edges = [2, 5, 9, 15, 24, 38, 58, 86, 120]
        for start in range(0, max(1, signal.size - frame + 1), hop):
            chunk = signal[start:start + frame]
            if chunk.size < frame:
                chunk = np.pad(chunk, (0, frame - chunk.size))
            spectrum = np.abs(np.fft.rfft(chunk * window)) ** 2
            bands = []
            for left, right in zip(edges[:-1], edges[1:]):
                bands.append(math.log1p(float(np.mean(spectrum[left:right]))))
            vectors.append(bands)
        if not vectors:
            return None
        spectral = np.mean(np.asarray(vectors, dtype=np.float32), axis=0)
        spectral_norm = float(np.linalg.norm(spectral))
        if spectral_norm <= 1e-8:
            return None
        spectral = spectral / spectral_norm

        # La envolvente temporal distingue dos voces simultáneas con espectro
        # parecido. Se interpola a longitud fija para tolerar pequeñas diferencias
        # de VAD entre micrófono y loopback.
        envelope_frame = max(80, int(target * 0.04))
        env = []
        for start in range(0, signal.size, envelope_frame):
            chunk = signal[start:start + envelope_frame]
            if chunk.size:
                env.append(float(np.sqrt(np.mean(chunk * chunk) + 1e-9)))
        if not env:
            return None
        env = np.asarray(env, dtype=np.float32)
        env_fixed = np.interp(
            np.linspace(0.0, 1.0, 12),
            np.linspace(0.0, 1.0, env.size),
            env,
        ).astype(np.float32)
        env_fixed -= float(np.mean(env_fixed))
        env_norm = float(np.linalg.norm(env_fixed))
        if env_norm > 1e-8:
            env_fixed /= env_norm
        vector = np.concatenate([spectral, env_fixed * 0.75])
        norm = float(np.linalg.norm(vector))
        vector = vector / max(norm, 1e-8)
        return tuple(float(x) for x in vector.tolist())

    @staticmethod
    def signature_similarity(a: Sequence[float] | None, b: Sequence[float] | None) -> float:
        if a is None or b is None or len(a) == 0 or len(b) == 0 or len(a) != len(b):
            return 0.0
        av = np.asarray(a, dtype=np.float32)
        bv = np.asarray(b, dtype=np.float32)
        denom = float(np.linalg.norm(av) * np.linalg.norm(bv))
        if denom <= 1e-9:
            return 0.0
        return float(np.dot(av, bv) / denom)

    @classmethod
    def same_source_audio(cls, first: TranscriptCandidate, second: TranscriptCandidate) -> bool:
        if first.label.casefold() == second.label.casefold():
            return False

        overlap = max(
            0.0,
            min(first.ended_at, second.ended_at) - max(first.started_at, second.started_at),
        )
        first_duration = max(0.1, first.ended_at - first.started_at)
        second_duration = max(0.1, second.ended_at - second.started_at)
        overlap_ratio = overlap / min(first_duration, second_duration)
        first_mid = (first.started_at + first.ended_at) / 2.0
        second_mid = (second.started_at + second.ended_at) / 2.0
        if overlap_ratio < 0.16 and abs(first_mid - second_mid) > 1.8:
            return False

        # El eco real puede transcribirse con palabras distintas. La firma
        # espectral permite eliminarlo aun cuando el texto no coincida bien.
        acoustic = cls.signature_similarity(first.audio_signature, second.audio_signature)
        spectral = 0.0
        if (
            first.audio_signature is not None
            and second.audio_signature is not None
            and len(first.audio_signature) >= 8
            and len(second.audio_signature) >= 8
        ):
            spectral = cls.signature_similarity(
                first.audio_signature[:8], second.audio_signature[:8]
            )
        if acoustic >= 0.93 and (overlap_ratio >= 0.18 or abs(first_mid - second_mid) <= 0.9):
            return True
        # El eco físico del headset cambia la envolvente temporal y el volumen,
        # pero conserva con mucha precisión la forma espectral del audio del PC.
        if spectral >= 0.985 and overlap_ratio >= 0.50:
            return True

        a = cls.normalize_text(first.text)
        b = cls.normalize_text(second.text)
        if not a or not b:
            return False
        a_words = a.split()
        b_words = b.split()
        minimum_words = min(len(a_words), len(b_words))
        if minimum_words < 3:
            return False
        if minimum_words >= 4 and (a in b or b in a):
            return True

        sequence = SequenceMatcher(None, a, b).ratio()
        a_set, b_set = set(a_words), set(b_words)
        containment = len(a_set & b_set) / max(1, min(len(a_set), len(b_set)))
        return (
            minimum_words >= 5 and (sequence >= 0.60 or containment >= 0.70)
        ) or (
            minimum_words >= 3 and sequence >= 0.86 and overlap_ratio >= 0.38
        )

    @staticmethod
    def hallucination(text: str) -> bool:
        cleaned = " ".join(str(text or "").casefold().split())
        words = re.findall(r"\w+", cleaned)
        if not words:
            return True

        noise_fragments = {
            "subtítulos", "subtitulos", "amara.org", "amara org",
            "suscríbete", "suscribete", "suscribirte", "suscríbase", "suscribase",
            "dale like", "deja un like", "activa la campanita",
            "gracias por ver", "hasta la próxima", "hasta la proxima",
        }
        if len(words) <= 14 and any(fragment in cleaned for fragment in noise_fragments):
            return True

        # Repetición patológica de una palabra o n-grama.
        if len(words) >= 5:
            repetition = max(words.count(word) for word in set(words)) / len(words)
            if repetition >= 0.55:
                return True
        if len(words) >= 9:
            unique_ratio = len(set(words)) / len(words)
            if unique_ratio <= 0.30:
                return True
            for size in (2, 3, 4, 5):
                if len(words) < size * 3:
                    continue
                grams = [tuple(words[i:i + size]) for i in range(len(words) - size + 1)]
                counts: dict[tuple[str, ...], int] = {}
                for gram in grams:
                    counts[gram] = counts.get(gram, 0) + 1
                top = max(counts.values(), default=0)
                if top >= 3 and top * size >= len(words) * 0.42:
                    return True
        return False
