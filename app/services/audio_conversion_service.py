from __future__ import annotations

import logging
import uuid
import wave
from pathlib import Path

import av
import numpy as np

from app.services.paths_service import AppPaths


class AudioConversionService:
    SUPPORTED_EXTENSIONS = {
        ".wav",
        ".mp3",
        ".m4a",
        ".flac",
        ".ogg",
        ".aac",
        ".wma",
        ".mp4",
        ".webm",
    }

    def __init__(self, paths: AppPaths) -> None:
        self._paths = paths
        self._logger = logging.getLogger(__name__)

    def convert_to_mono_wav(
        self,
        source: Path,
        progress_callback=None,
    ) -> Path:
        if not source.exists() or not source.is_file():
            raise FileNotFoundError(
                "EL ARCHIVO SELECCIONADO NO EXISTE."
            )

        if source.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(
                "FORMATO NO COMPATIBLE. USE WAV, MP3, M4A, FLAC, "
                "OGG, AAC, WMA, MP4 O WEBM."
            )

        output = (
            self._paths.temp
            / f"archivo_mono_{uuid.uuid4().hex}.wav"
        )

        try:
            if progress_callback:
                progress_callback(
                    4,
                    "ABRIENDO ARCHIVO...",
                )

            with av.open(str(source)) as container:
                stream = next(
                    (
                        item
                        for item in container.streams
                        if item.type == "audio"
                    ),
                    None,
                )

                if stream is None:
                    raise ValueError(
                        "EL ARCHIVO NO CONTIENE UNA PISTA DE AUDIO."
                    )

                resampler = av.audio.resampler.AudioResampler(
                    format="s16",
                    layout="mono",
                    rate=16000,
                )

                total_duration = 0.0

                if stream.duration is not None and stream.time_base is not None:
                    total_duration = float(
                        stream.duration * stream.time_base
                    )
                elif container.duration is not None:
                    total_duration = float(
                        container.duration
                    ) / 1_000_000.0

                frames_written = 0

                with wave.open(str(output), "wb") as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(16000)

                    for frame in container.decode(stream):
                        converted = resampler.resample(frame)

                        if converted is None:
                            continue

                        converted_frames = (
                            converted
                            if isinstance(converted, list)
                            else [converted]
                        )

                        for item in converted_frames:
                            array = item.to_ndarray()

                            if array.ndim > 1:
                                array = array.reshape(-1)

                            pcm = np.asarray(
                                array,
                                dtype=np.int16,
                            ).tobytes()

                            wav_file.writeframes(pcm)
                            frames_written += len(pcm) // 2

                        if (
                            progress_callback
                            and total_duration > 0
                            and frame.time is not None
                        ):
                            ratio = min(
                                max(
                                    float(frame.time)
                                    / total_duration,
                                    0.0,
                                ),
                                1.0,
                            )
                            progress_callback(
                                5 + int(ratio * 15),
                                "PREPARANDO AUDIO MONO...",
                            )

                if frames_written < 1600:
                    output.unlink(missing_ok=True)
                    raise ValueError(
                        "EL ARCHIVO NO CONTIENE AUDIO SUFICIENTE "
                        "PARA TRANSCRIBIR."
                    )

        except Exception:
            output.unlink(missing_ok=True)
            self._logger.exception(
                "NO FUE POSIBLE CONVERTIR EL ARCHIVO"
            )
            raise

        return output
