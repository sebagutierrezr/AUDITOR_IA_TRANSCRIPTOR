from __future__ import annotations

import os
import subprocess
import sys
import time
import wave
from pathlib import Path

import psutil

from app.services.paths_service import AppPaths


class NemoDiarizationService:
    """Diarización local con SortFormer, desacoplada del ASR.

    Separar ASR y diarización evita que un fallo o una demora del motor nativo
    impida obtener la transcripción completa. Si SortFormer falla, el llamador
    puede conservar el texto y aplicar una estrategia de respaldo.
    """

    def __init__(self) -> None:
        self.paths = AppPaths()

    @property
    def runtime(self) -> Path:
        candidates = [
            self.paths.nemo_speech / "bin" / "nemo-speech.exe",
            self.paths.bundle_root / "nemo-speech" / "bin" / "nemo-speech.exe",
            self.paths.root / "nemo-speech" / "bin" / "nemo-speech.exe",
        ]
        for path in candidates:
            if path.is_file():
                return path
        return candidates[0]

    @property
    def model(self) -> Path:
        candidates = [
            self.paths.models / "sortformer-v2-q8_0.gguf",
            self.paths.bundle_root / "models" / "sortformer-v2-q8_0.gguf",
        ]
        for path in candidates:
            if path.is_file():
                return path
        return candidates[0]

    def is_ready(self) -> bool:
        return self.runtime.is_file() and self.model.is_file()

    @staticmethod
    def _duration_seconds(wav_path: Path) -> float:
        try:
            with wave.open(str(wav_path), "rb") as handle:
                frames = handle.getnframes()
                rate = handle.getframerate() or 1
                return frames / float(rate)
        except Exception:
            return 0.0

    @staticmethod
    def _lower_priority(pid: int) -> None:
        try:
            proc = psutil.Process(pid)
            if os.name == "nt":
                proc.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
            cpus = psutil.cpu_count(logical=True) or 4
            if cpus >= 6:
                # Deja al menos dos hilos lógicos libres para Windows/UI.
                proc.cpu_affinity(list(range(max(2, cpus - 2))))
        except Exception:
            pass

    @staticmethod
    def _parse_rttm(path: Path) -> list[dict]:
        segments: list[dict] = []
        if not path.is_file():
            return segments

        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 8 or parts[0].upper() != "SPEAKER":
                continue
            try:
                start = float(parts[3])
                duration = float(parts[4])
            except ValueError:
                continue
            speaker = str(parts[7])
            end = max(start, start + max(0.0, duration))
            segments.append({"start": start, "end": end, "speaker": speaker})

        segments.sort(key=lambda item: (item["start"], item["end"]))
        return segments

    def diarize(self, wav_path: Path, progress=None) -> list[dict]:
        if not self.is_ready():
            raise RuntimeError("SORTFORMER NO ESTA INSTALADO O ESTA INCOMPLETO.")

        output = self.paths.temp / f"{wav_path.stem}_{int(time.time() * 1000)}.rttm"
        output.unlink(missing_ok=True)

        duration = self._duration_seconds(wav_path)
        cmd = [
            str(self.runtime),
            "diarize",
            str(wav_path),
            "--model",
            str(self.model),
            "--format",
            "rttm",
            "--output",
            str(output),
        ]
        # SortFormer full-attention (--offline) está pensado para audios cortos.
        # Para llamadas largas usamos el modo streaming por defecto: consume menos
        # memoria y evita aparentes bloqueos en grabaciones extensas.
        if 0.0 < duration <= 360.0:
            cmd.append("--offline")

        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        env = os.environ.copy()
        env.setdefault("OMP_NUM_THREADS", str(max(2, min(6, (os.cpu_count() or 4) - 2))))
        env.setdefault("TOKENIZERS_PARALLELISM", "false")

        if progress:
            progress(72, "SEPARANDO VOCES CON SORTFORMER...")

        log_path = output.with_suffix(".nemo.log")
        log_path.unlink(missing_ok=True)
        log_handle = log_path.open("w", encoding="utf-8", errors="replace")
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=flags,
                env=env,
            )
        except Exception:
            log_handle.close()
            raise
        self._lower_priority(proc.pid)

        timeout_seconds = min(1500.0, max(120.0, duration * 3.0 + 75.0))
        started = time.monotonic()
        last_progress = -1

        try:
            while proc.poll() is None:
                elapsed = time.monotonic() - started
                if elapsed > timeout_seconds:
                    proc.kill()
                    raise TimeoutError(
                        "SORTFORMER EXCEDIO EL TIEMPO MAXIMO. LA TRANSCRIPCION SE CONSERVARA SIN DIARIZACION ACUSTICA."
                    )

                if progress:
                    ratio = min(1.0, elapsed / max(1.0, timeout_seconds))
                    value = 72 + int(ratio * 14)
                    if value != last_progress:
                        last_progress = value
                        progress(value, "SEPARANDO VOCES CON SORTFORMER...")
                time.sleep(0.20)

            proc.wait(timeout=10)
        finally:
            if proc.poll() is None:
                proc.kill()
                try:
                    proc.wait(timeout=5)
                except Exception:
                    pass
            log_handle.close()

        if proc.returncode != 0:
            detail = ""
            try:
                detail = log_path.read_text(encoding="utf-8", errors="replace").strip()[-1800:]
            except Exception:
                pass
            log_path.unlink(missing_ok=True)
            output.unlink(missing_ok=True)
            raise RuntimeError("SORTFORMER FALLO: " + (detail or f"codigo {proc.returncode}"))

        segments = self._parse_rttm(output)
        output.unlink(missing_ok=True)
        log_path.unlink(missing_ok=True)
        if not segments:
            raise RuntimeError("SORTFORMER FINALIZO SIN SEGMENTOS DE HABLANTE.")

        if progress:
            progress(87, "VOCES DETECTADAS. ASIGNANDO PALABRAS...")
        return segments
