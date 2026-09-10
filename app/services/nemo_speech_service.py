from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

from app.services.paths_service import AppPaths
from app.services.role_classifier import infer_role_map, refine_turn_roles


class NemoSpeechService:
    def __init__(self):
        self.paths = AppPaths()

    @property
    def runtime(self) -> Path:
        root = Path(getattr(sys, "_MEIPASS", self.paths.root))
        candidates = [
            root / "nemo-speech" / "bin" / "nemo-speech.exe",
            self.paths.root / "nemo-speech" / "bin" / "nemo-speech.exe",
            root / "runtime" / "nemo-speech.exe",
        ]
        for path in candidates:
            if path.is_file():
                return path
        return candidates[0]

    @property
    def asr_model(self) -> Path:
        root = Path(getattr(sys, "_MEIPASS", self.paths.root))
        for path in [
            root / "models" / "nemotron-3.5-asr-streaming-0.6b.q8_0.gguf",
            self.paths.models / "nemotron-3.5-asr-streaming-0.6b.q8_0.gguf",
        ]:
            if path.is_file():
                return path
        return root / "models" / "nemotron-3.5-asr-streaming-0.6b.q8_0.gguf"

    @property
    def diar_model(self) -> Path:
        root = Path(getattr(sys, "_MEIPASS", self.paths.root))
        for path in [
            root / "models" / "sortformer-v2-q8_0.gguf",
            self.paths.models / "sortformer-v2-q8_0.gguf",
        ]:
            if path.is_file():
                return path
        return root / "models" / "sortformer-v2-q8_0.gguf"

    def is_ready(self):
        return self.runtime.is_file() and self.asr_model.is_file() and self.diar_model.is_file()

    @staticmethod
    def _collect_words(obj):
        found = []

        def walk(value):
            if isinstance(value, dict):
                if (
                    ("word" in value or "text" in value)
                    and any(key in value for key in ("speaker_tag", "speaker", "speaker_id"))
                    and any(key in value for key in ("start_time", "start", "start_sec"))
                ):
                    found.append(value)
                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)

        walk(obj)
        return found

    @staticmethod
    def _seconds(value):
        try:
            number = float(value)
        except Exception:
            return 0.0
        # Riva-shaped JSON suele usar ms; otros builds usan segundos.
        return number / 1000.0 if number > 1000 else number

    @staticmethod
    def _clean_token(text: str) -> str:
        text = str(text or "")
        # Quita artefactos de idioma/control observados en algunos builds:
        # <ES-ES>, <|es|>, etc., sin tocar el contenido normal.
        text = re.sub(r"<\|?[^>]{1,32}\|?>", "", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @staticmethod
    def _join_words(words: list[dict]) -> str:
        # El CLI entrega tokens que pueden venir con o sin espacio inicial.
        # Para la salida visual preferimos una reconstrucción legible y estable.
        parts = [str(item.get("text", "")).strip() for item in words]
        return re.sub(r"\s+", " ", " ".join(part for part in parts if part)).strip()

    def transcribe(
        self,
        wav: Path,
        agent_label="AGENTE",
        client_label="CLIENTE",
        uppercase=True,
        progress=None,
    ):
        if not self.is_ready():
            raise RuntimeError("MOTOR NEMO/SORTFORMER NO ESTA INSTALADO O ESTA INCOMPLETO.")

        cmd = [
            str(self.runtime),
            "transcribe",
            str(wav),
            "--model",
            str(self.asr_model),
            "--diar-model",
            str(self.diar_model),
            "--diar-preset",
            "offline",
            "--json",
            "--word-times",
            "--device",
            "cpu",
            "--language",
            "es-ES",
        ]

        if progress:
            progress(30, "NEMOTRON 3.5 + SORTFORMER: TRANSCRIBIENDO Y SEPARANDO VOCES...")

        flags = 0
        if os.name == "nt":
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=flags,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                "NEMO-SPEECH FALLO: " + (proc.stderr[-1200:] or proc.stdout[-1200:])
            )

        raw = proc.stdout.strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            starts = [index for index in (raw.find("{"), raw.find("[")) if index >= 0]
            first = min(starts, default=-1)
            if first < 0:
                raise RuntimeError("NEMO-SPEECH NO DEVOLVIO JSON ESTRUCTURADO.")
            data = json.loads(raw[first:])

        words = self._collect_words(data)
        if not words:
            raise RuntimeError("NEMO-SPEECH NO DEVOLVIO PALABRAS CON SPEAKER TAG.")

        normalized = []
        for word in words:
            text = self._clean_token(word.get("word", word.get("text", "")))
            if not text:
                continue

            speaker = str(
                word.get("speaker_tag", word.get("speaker", word.get("speaker_id", "0")))
            )
            start = self._seconds(word.get("start_time", word.get("start", word.get("start_sec", 0))))
            end = self._seconds(word.get("end_time", word.get("end", word.get("end_sec", start))))

            normalized.append(
                {
                    "text": text,
                    "speaker": speaker,
                    "start": start,
                    "end": max(start, end),
                }
            )

        normalized.sort(key=lambda item: (item["start"], item["end"]))

        # Reconstituye intervenciones desde speaker tags por palabra. Mantiene
        # pausas cortas del mismo hablante y corta inmediatamente al cambiar voz.
        turns = []
        for word in normalized:
            if (
                turns
                and turns[-1]["speaker"] == word["speaker"]
                and word["start"] - turns[-1]["end"] <= 0.75
            ):
                turns[-1]["words"].append(word)
                turns[-1]["end"] = max(turns[-1]["end"], word["end"])
            else:
                turns.append(
                    {
                        "speaker": word["speaker"],
                        "start": word["start"],
                        "end": word["end"],
                        "words": [word],
                    }
                )

        for turn in turns:
            turn["text"] = self._join_words(turn["words"])

        if progress:
            progress(91, "DETERMINANDO MAPA GLOBAL DE AGENTE Y CLIENTE...")

        role_map = infer_role_map(turns, agent_label, client_label)

        if progress:
            progress(94, "AFINANDO ROLES POR CONTEXTO Y CORRIGIENDO BORDES...")

        refined_turns = refine_turn_roles(
            turns,
            role_map,
            agent_label=agent_label,
            client_label=client_label,
        )

        out = []
        for turn in refined_turns:
            label = str(turn.get("role", role_map.get(turn.get("speaker"), "HABLANTE")))
            body = self._join_words(list(turn.get("words", []) or [])) or str(turn.get("text", "")).strip()
            body = body.upper() if uppercase else body
            start = float(turn.get("start", 0.0))
            end = float(turn.get("end", start))

            out.append(
                {
                    "start": start,
                    "end": end,
                    "speaker": label,
                    "text": f"[{start:07.2f}] {label}: {body}",
                    "words": list(turn.get("words", []) or []),
                }
            )

        if progress:
            progress(98, "AGENTE Y CLIENTE REVISADOS · SPEAKER ROLE V3")

        return out
