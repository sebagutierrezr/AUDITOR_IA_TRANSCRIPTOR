from __future__ import annotations

import logging
import os
import threading
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.models.conversation import Conversation
from app.services.paths_service import AppPaths


@dataclass(frozen=True)
class SpeakerTurn:
    start: float
    end: float
    speaker: str

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


class DiarizationService:
    """
    Diarización neuronal local para exactamente dos participantes.

    Utiliza pyannote Community-1 y su salida exclusiva para reconciliar
    de forma más estable los tiempos de Whisper con los cambios de voz.
    """

    MODEL_FOLDER = "pyannote-community-1"
    REQUIRED_MARKERS = (
        "config.yaml",
    )

    _pipeline = None
    _pipeline_lock = threading.RLock()

    def __init__(self) -> None:
        self._paths = AppPaths()
        self._logger = logging.getLogger(__name__)

    @property
    def model_path(self) -> Path:
        return self._paths.models / self.MODEL_FOLDER

    def is_ready(self) -> bool:
        path = self.model_path

        if not path.is_dir():
            return False

        return all(
            (path / marker).is_file()
            and (path / marker).stat().st_size > 0
            for marker in self.REQUIRED_MARKERS
        )

    def readiness_message(self) -> str:
        return (
            "IDENTIFICADOR DE VOCES: LISTO"
            if self.is_ready()
            else "IDENTIFICADOR DE VOCES: NO DISPONIBLE"
        )

    def diarize(
        self,
        conversation: Conversation,
        audio_path: Path,
        speaker_one_label: str,
        speaker_two_label: str,
        first_speaker_is_one: bool,
        progress_callback=None,
    ) -> Conversation:
        if not self.is_ready():
            raise RuntimeError(
                "EL MODELO DE IDENTIFICACIÓN DE VOCES "
                "NO ESTÁ INSTALADO O ESTÁ INCOMPLETO."
            )

        if len(conversation.segments) < 1:
            return conversation

        if progress_callback:
            progress_callback(
                90,
                "CARGANDO IDENTIFICADOR DE VOCES...",
            )

        pipeline = self._load_pipeline()

        if progress_callback:
            progress_callback(
                92,
                "IDENTIFICANDO DOS PARTICIPANTES...",
            )

        waveform, sample_rate = self._read_waveform(audio_path)

        import torch

        tensor = torch.from_numpy(
            waveform
        ).unsqueeze(0)

        with torch.inference_mode():
            result = pipeline(
                {
                    "waveform": tensor,
                    "sample_rate": sample_rate,
                },
                num_speakers=2,
            )

        diarization = getattr(
            result,
            "exclusive_speaker_diarization",
            None,
        )

        if diarization is None:
            diarization = getattr(
                result,
                "speaker_diarization",
                result,
            )

        turns = self._extract_turns(diarization)

        if len(turns) < 2:
            raise RuntimeError(
                "NO FUE POSIBLE CONFIRMAR DOS VOCES "
                "DIFERENTES EN EL ARCHIVO."
            )

        unique_speakers = {
            turn.speaker
            for turn in turns
        }

        if len(unique_speakers) != 2:
            raise RuntimeError(
                "EL IDENTIFICADOR NO PUDO ESTABLECER "
                "EXACTAMENTE DOS PARTICIPANTES."
            )

        first_speaker = min(
            turns,
            key=lambda turn: (
                turn.start,
                -turn.duration,
            ),
        ).speaker
        other_speaker = next(
            speaker
            for speaker in unique_speakers
            if speaker != first_speaker
        )

        if first_speaker_is_one:
            speaker_map = {
                first_speaker: speaker_one_label,
                other_speaker: speaker_two_label,
            }
        else:
            speaker_map = {
                first_speaker: speaker_two_label,
                other_speaker: speaker_one_label,
            }

        if progress_callback:
            progress_callback(
                97,
                "ASIGNANDO AGENTE Y CLIENTE...",
            )

        previous_label = None

        for segment in conversation.segments:
            raw_speaker, confidence = self._best_speaker(
                segment.start,
                segment.end,
                turns,
            )

            if raw_speaker is None:
                raw_speaker = self._nearest_speaker(
                    segment.start,
                    segment.end,
                    turns,
                )

            label = speaker_map[raw_speaker]

            # Solo reutiliza la etiqueta anterior en intervalos realmente
            # ambiguos y contiguos. Nunca alterna hablantes artificialmente.
            if (
                confidence < 0.20
                and previous_label is not None
            ):
                label = previous_label

            segment.speaker = label
            segment.text = self._apply_label(
                segment.text,
                label,
            )
            previous_label = label

        if progress_callback:
            progress_callback(
                99,
                "AGENTE Y CLIENTE IDENTIFICADOS",
            )

        return conversation

    def _load_pipeline(self):
        with self._pipeline_lock:
            if self.__class__._pipeline is not None:
                return self.__class__._pipeline

            import torch
            from pyannote.audio import Pipeline

            available = max(
                1,
                os.cpu_count() or 2,
            )
            torch.set_num_threads(
                max(
                    1,
                    min(6, available - 1),
                )
            )

            pipeline = Pipeline.from_pretrained(
                str(self.model_path)
            )
            pipeline.to(
                torch.device("cpu")
            )

            self.__class__._pipeline = pipeline
            return pipeline

    @staticmethod
    def _read_waveform(
        audio_path: Path,
    ) -> tuple[np.ndarray, int]:
        """
        Lee el WAV mono preparado por la aplicación.

        Se entrega la forma de onda en memoria para evitar que pyannote
        dependa de FFmpeg o de los decodificadores del equipo del usuario.
        """
        with wave.open(
            str(audio_path),
            "rb",
        ) as wav_file:
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            sample_rate = wav_file.getframerate()
            frames = wav_file.readframes(
                wav_file.getnframes()
            )

        if sample_width != 2:
            raise RuntimeError(
                "EL AUDIO PREPARADO NO TIENE FORMATO PCM DE 16 BITS."
            )

        audio = np.frombuffer(
            frames,
            dtype=np.int16,
        ).astype(np.float32)

        if channels > 1:
            audio = audio.reshape(
                -1,
                channels,
            ).mean(axis=1)

        if audio.size == 0:
            raise RuntimeError(
                "EL AUDIO PREPARADO ESTÁ VACÍO."
            )

        audio /= 32768.0
        return audio, sample_rate

    @staticmethod
    def _extract_turns(
        diarization,
    ) -> list[SpeakerTurn]:
        turns = []

        try:
            iterator = diarization.itertracks(
                yield_label=True
            )
            for turn, _, speaker in iterator:
                turns.append(
                    SpeakerTurn(
                        start=float(turn.start),
                        end=float(turn.end),
                        speaker=str(speaker),
                    )
                )
        except AttributeError:
            for turn, speaker in diarization:
                turns.append(
                    SpeakerTurn(
                        start=float(turn.start),
                        end=float(turn.end),
                        speaker=str(speaker),
                    )
                )

        return sorted(
            (
                turn
                for turn in turns
                if turn.duration > 0
            ),
            key=lambda turn: (
                turn.start,
                turn.end,
            ),
        )

    @staticmethod
    def _best_speaker(
        start: float,
        end: float,
        turns: list[SpeakerTurn],
    ) -> tuple[str | None, float]:
        segment_duration = max(
            0.05,
            end - start,
        )
        overlap_by_speaker: dict[str, float] = {}

        for turn in turns:
            overlap = max(
                0.0,
                min(end, turn.end)
                - max(start, turn.start),
            )

            if overlap <= 0:
                continue

            overlap_by_speaker[turn.speaker] = (
                overlap_by_speaker.get(
                    turn.speaker,
                    0.0,
                )
                + overlap
            )

        if not overlap_by_speaker:
            return None, 0.0

        speaker, overlap = max(
            overlap_by_speaker.items(),
            key=lambda item: item[1],
        )
        confidence = min(
            1.0,
            overlap / segment_duration,
        )
        return speaker, confidence

    @staticmethod
    def _nearest_speaker(
        start: float,
        end: float,
        turns: list[SpeakerTurn],
    ) -> str:
        midpoint = (
            start + end
        ) / 2.0

        nearest = min(
            turns,
            key=lambda turn: min(
                abs(midpoint - turn.start),
                abs(midpoint - turn.end),
            ),
        )
        return nearest.speaker

    @staticmethod
    def _apply_label(
        text: str,
        speaker: str,
    ) -> str:
        import re

        timestamp = re.match(
            r"^(\[[^\]]+\]\s*)(.*)$",
            text,
            flags=re.DOTALL,
        )

        if timestamp:
            prefix, body = timestamp.groups()
            body = re.sub(
                r"^\s*[^:\n]{1,40}:\s*",
                "",
                body,
                count=1,
            )
            return (
                f"{prefix}{speaker}: "
                f"{body.strip()}"
            )

        body = re.sub(
            r"^\s*[^:\n]{1,40}:\s*",
            "",
            text,
            count=1,
        )
        return (
            f"{speaker}: "
            f"{body.strip()}"
        )

    @classmethod
    def release(cls) -> None:
        with cls._pipeline_lock:
            cls._pipeline = None
