from __future__ import annotations

import base64
import json
import logging
import mimetypes
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

from app.models.conversation import Conversation, Segment


class HighPrecisionTranscriptionService:
    TRANSCRIPTION_MODEL = "gpt-4o-transcribe-diarize"
    DEFAULT_ROLE_MODEL = "gpt-5.6-luna"
    MAX_BYTES = 25 * 1024 * 1024
    SUPPORTED = {
        ".mp3",
        ".mp4",
        ".mpeg",
        ".mpga",
        ".m4a",
        ".ogg",
        ".wav",
        ".webm",
    }

    AGENT_MARKERS = (
        "mi nombre es",
        "le habla",
        "me comunico",
        "me estoy comunicando",
        "llamo de",
        "llamamos de",
        "encuesta",
        "entrevista",
        "unas preguntas",
        "algunas preguntas",
        "en una escala",
        "que nota",
        "qué nota",
        "podria indicarme",
        "podría indicarme",
        "me podria indicar",
        "me podría indicar",
        "para finalizar",
        "ultima pregunta",
        "última pregunta",
        "muchas gracias por su tiempo",
        "gracias por su tiempo",
    )

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)

    def transcribe(
        self,
        audio_path: Path,
        api_key: str,
        language: str = "ES",
        uppercase: bool = True,
        show_timestamps: bool = True,
        agent_label: str = "AGENTE",
        client_label: str = "CLIENTE",
        role_model: str = DEFAULT_ROLE_MODEL,
        agent_reference_path: str = "",
        progress_callback=None,
    ) -> Conversation:
        self._validate_audio(audio_path)
        if not api_key.strip():
            raise RuntimeError("No hay una API key configurada.")

        self._emit(progress_callback, 5, "PREPARANDO ARCHIVO...")

        from openai import OpenAI
        import openai

        client = OpenAI(api_key=api_key.strip(), timeout=900.0, max_retries=2)
        payload = {
            "model": self.TRANSCRIPTION_MODEL,
            "response_format": "diarized_json",
            "chunking_strategy": "auto",
        }
        if language and language.upper() != "AUTO":
            payload["language"] = language.lower()

        reference = Path(agent_reference_path) if agent_reference_path else None
        reference_used = bool(reference and reference.is_file())
        if reference_used:
            # La guía oficial del SDK usa extra_body para las referencias
            # conocidas del modelo de diarización.
            payload["extra_body"] = {
                "known_speaker_names": ["AGENTE_REFERENCIA"],
                "known_speaker_references": [self._data_url(reference)],
            }

        self._emit(
            progress_callback,
            -1,
            "TRANSCRIBIENDO Y SEPARANDO HABLANTES CON ALTA PRECISIÓN...",
        )

        try:
            response = self._create_transcription(client, audio_path, payload)
        except openai.AuthenticationError as exc:
            raise RuntimeError("La API key no es válida o fue revocada.") from exc
        except openai.RateLimitError as exc:
            raise RuntimeError(
                "La cuenta API no tiene cupo disponible o alcanzó un límite de uso."
            ) from exc
        except openai.APIConnectionError as exc:
            raise RuntimeError(
                "No fue posible conectar con OpenAI. Revisa la conexión a Internet."
            ) from exc
        except openai.APIStatusError as exc:
            message = getattr(exc, "message", "") or str(exc)
            raise RuntimeError(f"OpenAI devolvió un error: {message}") from exc

        segments = self._extract_segments(response)
        speakers = self._speakers(segments)

        if len(speakers) < 2:
            self.logger.warning(
                "Primer intento detectó %s hablante(s). Reintentando con VAD sensible.",
                len(speakers),
            )
            retry_payload = dict(payload)
            retry_payload["chunking_strategy"] = {
                "type": "server_vad",
                "threshold": 0.25,
                "prefix_padding_ms": 500,
                "silence_duration_ms": 300,
            }
            self._emit(
                progress_callback, -1, "REINTENTANDO SEPARACIÓN DE HABLANTES..."
            )
            response = self._create_transcription(client, audio_path, retry_payload)
            segments = self._extract_segments(response)
            speakers = self._speakers(segments)

        if len(speakers) < 2:
            raise RuntimeError(
                "El servicio solo pudo confirmar un hablante en este audio. "
                "Para auditoría no se publicará una separación insegura. "
                "En Ajustes puedes cargar una muestra de 2 a 10 segundos de la voz del agente."
            )

        self._emit(
            progress_callback,
            78,
            "IDENTIFICANDO QUIÉN ES AGENTE Y QUIÉN ES CLIENTE...",
        )

        role_map, role_confidence, reason = self._resolve_roles(
            client=client,
            segments=segments,
            speakers=speakers,
            agent_label=agent_label,
            client_label=client_label,
            role_model=role_model or self.DEFAULT_ROLE_MODEL,
            reference_used=reference_used,
        )

        self._emit(progress_callback, 90, "ORDENANDO INTERVENCIONES...")
        final = self._build_segments(
            segments=segments,
            role_map=role_map,
            uppercase=uppercase,
            show_timestamps=show_timestamps,
        )

        if not final:
            raise RuntimeError("La transcripción no devolvió contenido utilizable.")

        self._emit(progress_callback, 100, "TRANSCRIPCIÓN FINALIZADA")
        return Conversation(
            source_path=str(audio_path),
            language=language.upper() if language else "AUTO",
            segments=final,
            speaker_count=len(speakers),
            role_confidence=role_confidence,
            role_reason=reason,
        )

    def validate_key(self, api_key: str) -> tuple[bool, str]:
        from openai import OpenAI
        import openai

        try:
            client = OpenAI(api_key=api_key.strip(), timeout=25.0, max_retries=0)
            client.models.retrieve(self.TRANSCRIPTION_MODEL)
            return True, "CONEXIÓN CORRECTA · ALTA PRECISIÓN DISPONIBLE"
        except openai.AuthenticationError:
            return False, "API KEY INVÁLIDA O REVOCADA"
        except openai.RateLimitError:
            return (
                False,
                "LA CLAVE ES VÁLIDA, PERO LA CUENTA NO TIENE CUPO DISPONIBLE",
            )
        except openai.PermissionDeniedError:
            return False, "LA CUENTA NO TIENE ACCESO AL MODELO DE DIARIZACIÓN"
        except openai.APIConnectionError:
            return False, "NO FUE POSIBLE CONECTAR CON OPENAI"
        except Exception as exc:
            return False, f"NO FUE POSIBLE VALIDAR: {exc}"

    @staticmethod
    def _create_transcription(client, audio_path: Path, payload: dict):
        with audio_path.open("rb") as audio_file:
            return client.audio.transcriptions.create(file=audio_file, **payload)

    @staticmethod
    def _extract_segments(response) -> list[dict]:
        rows = []
        raw_segments = getattr(response, "segments", None) or []
        for item in raw_segments:
            if hasattr(item, "model_dump"):
                item = item.model_dump()
            elif not isinstance(item, dict):
                item = {
                    "speaker": getattr(item, "speaker", ""),
                    "start": getattr(item, "start", 0.0),
                    "end": getattr(item, "end", 0.0),
                    "text": getattr(item, "text", ""),
                }
            text = str(item.get("text", "") or "").strip()
            speaker = str(item.get("speaker", "") or "").strip()
            if not text or not speaker:
                continue
            rows.append(
                {
                    "speaker": speaker,
                    "start": float(item.get("start", 0.0) or 0.0),
                    "end": float(item.get("end", 0.0) or 0.0),
                    "text": text,
                }
            )
        return rows

    @staticmethod
    def _speakers(segments: list[dict]) -> list[str]:
        durations = defaultdict(float)
        order = []
        for row in segments:
            speaker = row["speaker"]
            if speaker not in order:
                order.append(speaker)
            durations[speaker] += max(0.0, row["end"] - row["start"])
        return sorted(order, key=lambda s: durations[s], reverse=True)

    def _resolve_roles(
        self,
        client,
        segments,
        speakers,
        agent_label,
        client_label,
        role_model,
        reference_used,
    ):
        if reference_used:
            for speaker in speakers:
                normalized = self._normalize(speaker)
                if normalized in {"agente_referencia", "agente referencia"}:
                    other = next((s for s in speakers if s != speaker), None)
                    if other:
                        return (
                            {speaker: agent_label, other: client_label},
                            0.99,
                            "Agente identificado mediante muestra de voz conocida.",
                        )

        transcript = "\n".join(
            f"{row['speaker']}: {row['text']}" for row in segments[:180]
        )[:50000]

        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "agent_speaker": {"type": "string"},
                "client_speaker": {"type": "string"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "reason": {"type": "string"},
            },
            "required": [
                "agent_speaker",
                "client_speaker",
                "confidence",
                "reason",
            ],
        }

        try:
            result = client.responses.create(
                model=role_model,
                reasoning={"effort": "low"},
                input=[
                    {
                        "role": "developer",
                        "content": (
                            "Analiza una entrevista telefónica ya diarizada. Debes identificar cuál speaker es el AGENTE/ENCUESTADOR "
                            "y cuál es el CLIENTE/ENTREVISTADO. El agente conduce la entrevista, se presenta, hace las preguntas, "
                            "lee escalas, sondea y cierra. El cliente responde, entrega notas y relata su experiencia. "
                            "No asumas que el primero en hablar es el agente. Usa solo los speaker IDs existentes."
                        ),
                    },
                    {"role": "user", "content": transcript},
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "speaker_roles",
                        "strict": True,
                        "schema": schema,
                    },
                    "verbosity": "low",
                },
            )
            data = json.loads(result.output_text)
            agent = str(data["agent_speaker"]).strip()
            client_speaker = str(data["client_speaker"]).strip()
            confidence = float(data["confidence"])
            if (
                agent in speakers
                and client_speaker in speakers
                and agent != client_speaker
            ):
                mapping = {agent: agent_label, client_speaker: client_label}
                for extra in speakers:
                    mapping.setdefault(extra, "OTRO")
                return mapping, confidence, str(data["reason"]).strip()
        except Exception:
            self.logger.exception(
                "Fallo clasificación semántica de roles; usando fallback estructural."
            )

        return self._heuristic_roles(
            segments, speakers, agent_label, client_label
        )

    def _heuristic_roles(self, segments, speakers, agent_label, client_label):
        scores = {s: 0.0 for s in speakers}
        for row in segments:
            speaker = row["speaker"]
            text = self._normalize(row["text"])
            score = 0.0
            if "?" in row["text"] or "¿" in row["text"]:
                score += 2.5
            for marker in self.AGENT_MARKERS:
                if self._normalize(marker) in text:
                    score += 4.0
            words = text.split()
            if len(words) <= 4 and re.search(
                r"\b(?:[1-9]|10|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|si|no)\b",
                text,
            ):
                score -= 2.0
            scores[speaker] += score

        ordered = sorted(scores, key=scores.get, reverse=True)
        agent = ordered[0]
        client_speaker = ordered[1]
        delta = scores[agent] - scores[client_speaker]
        confidence = max(0.55, min(0.88, 0.60 + delta / 40.0))
        mapping = {agent: agent_label, client_speaker: client_label}
        for extra in speakers:
            mapping.setdefault(extra, "OTRO")
        return (
            mapping,
            confidence,
            "Rol asignado por estructura de preguntas y respuestas.",
        )

    def _build_segments(self, segments, role_map, uppercase, show_timestamps):
        merged = []
        for row in sorted(segments, key=lambda r: (r["start"], r["end"])):
            label = role_map.get(row["speaker"], "OTRO")
            text = row["text"].strip()
            if uppercase:
                text = text.upper()

            if (
                merged
                and merged[-1]["label"] == label
                and row["start"] - merged[-1]["end"] <= 1.2
            ):
                merged[-1]["end"] = max(merged[-1]["end"], row["end"])
                merged[-1]["text"] = (
                    merged[-1]["text"].rstrip() + " " + text.lstrip()
                ).strip()
            else:
                merged.append(
                    {
                        "label": label,
                        "start": row["start"],
                        "end": row["end"],
                        "text": text,
                    }
                )

        output = []
        for row in merged:
            prefix = (
                f"[{self._format_time(row['start'])} - {self._format_time(row['end'])}] "
                if show_timestamps
                else ""
            )
            output.append(
                Segment(
                    start=row["start"],
                    end=row["end"],
                    speaker=row["label"],
                    text=f"{prefix}{row['label']}: {row['text']}",
                )
            )
        return output

    def _validate_audio(self, audio_path: Path) -> None:
        if not audio_path.is_file():
            raise FileNotFoundError("El archivo seleccionado no existe.")
        if audio_path.suffix.lower() not in self.SUPPORTED:
            raise RuntimeError(
                "Formato no compatible. Usa MP3, WAV, M4A, MP4, OGG, MPEG/MPGA o WEBM."
            )
        if audio_path.stat().st_size > self.MAX_BYTES:
            raise RuntimeError(
                "El archivo supera 25 MB. Esta versión procesa archivos de hasta 25 MB por solicitud."
            )

    @staticmethod
    def _data_url(path: Path) -> str:
        mime = mimetypes.guess_type(str(path))[0] or "audio/wav"
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{encoded}"

    @staticmethod
    def _normalize(text: str) -> str:
        value = unicodedata.normalize("NFD", (text or "").casefold())
        value = "".join(
            ch for ch in value if unicodedata.category(ch) != "Mn"
        )
        value = re.sub(r"[^a-z0-9_\s]", " ", value)
        return re.sub(r"\s+", " ", value).strip()

    @staticmethod
    def _format_time(seconds: float) -> str:
        total = max(0, int(seconds))
        minutes, secs = divmod(total, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    @staticmethod
    def _emit(callback, value: int, message: str) -> None:
        if callback:
            callback(value, message)
