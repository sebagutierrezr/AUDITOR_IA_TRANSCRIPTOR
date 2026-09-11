from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from app.engines.faster_whisper_engine import FasterWhisperEngine
from app.models.conversation import Conversation
from app.services.nemo_diarization_service import NemoDiarizationService
from app.services.role_classifier import infer_role_map, refine_turn_roles, score_role_text


class FileTranscriptionService:
    """ASR estable + diarización desacoplada.

    Faster-Whisper genera texto y timestamps por palabra. SortFormer se usa solo
    para la huella acústica de hablantes. Si SortFormer falla, el texto se entrega
    igualmente con un respaldo contextual en vez de perder toda la transcripción.
    """

    def __init__(self, performance_mode: str = "AUTO") -> None:
        self.asr = FasterWhisperEngine("ALTA", performance_mode)
        self.diar = NemoDiarizationService()

    @staticmethod
    def _flatten_words(conversation: Conversation) -> list[dict]:
        words: list[dict] = []
        for segment in conversation.segments:
            raw_words = list(segment.words or [])
            if raw_words:
                for word in raw_words:
                    text = str(word.get("text", "")).strip()
                    if not text:
                        continue
                    start = float(word.get("start", segment.start))
                    end = float(word.get("end", segment.end))
                    words.append(
                        {
                            "text": text,
                            "start": start,
                            "end": max(start, end),
                            "probability": word.get("probability"),
                        }
                    )
            else:
                text = str(segment.text or "").strip()
                if text:
                    words.append(
                        {
                            "text": text,
                            "start": float(segment.start),
                            "end": float(segment.end),
                            "probability": segment.confidence,
                        }
                    )
        words.sort(key=lambda item: (item["start"], item["end"]))
        return words

    @staticmethod
    def _speaker_for_word(word: dict, diar_segments: list[dict], previous: str = "") -> str:
        ws = float(word["start"])
        we = float(word["end"])
        center = (ws + we) / 2.0

        best_speaker = ""
        best_overlap = 0.0
        nearest_speaker = ""
        nearest_distance = float("inf")

        for segment in diar_segments:
            ss = float(segment["start"])
            se = float(segment["end"])
            overlap = max(0.0, min(we, se) - max(ws, ss))
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = str(segment["speaker"])

            if ss <= center <= se:
                return str(segment["speaker"])

            distance = min(abs(center - ss), abs(center - se))
            if distance < nearest_distance:
                nearest_distance = distance
                nearest_speaker = str(segment["speaker"])

        if best_speaker:
            return best_speaker
        if nearest_speaker and nearest_distance <= 0.75:
            return nearest_speaker
        return previous or nearest_speaker or "speaker_0"

    @classmethod
    def _turns_from_diarization(cls, words: list[dict], diar_segments: list[dict]) -> list[dict]:
        enriched: list[dict] = []
        previous = ""
        for word in words:
            speaker = cls._speaker_for_word(word, diar_segments, previous)
            previous = speaker
            enriched.append({**word, "speaker": speaker})

        turns: list[dict] = []
        for word in enriched:
            if (
                turns
                and turns[-1]["speaker"] == word["speaker"]
                and float(word["start"]) - float(turns[-1]["end"]) <= 1.15
            ):
                turns[-1]["words"].append(word)
                turns[-1]["end"] = max(float(turns[-1]["end"]), float(word["end"]))
            else:
                turns.append(
                    {
                        "speaker": word["speaker"],
                        "start": float(word["start"]),
                        "end": float(word["end"]),
                        "words": [word],
                    }
                )

        for turn in turns:
            turn["text"] = " ".join(
                str(item.get("text", "")).strip() for item in turn["words"] if str(item.get("text", "")).strip()
            ).strip()
        return [turn for turn in turns if turn.get("text")]

    @staticmethod
    def _fallback_turns(conversation: Conversation, agent_label: str, client_label: str) -> list[dict]:
        """Respaldo contextual si la diarización acústica no está disponible."""
        turns: list[dict] = []
        previous_role = client_label

        for index, segment in enumerate(conversation.segments):
            text = str(segment.text or "").strip()
            if not text:
                continue
            a, c = score_role_text(text)
            if a - c >= 3.0:
                role = agent_label
            elif c - a >= 3.0:
                role = client_label
            else:
                # En una entrevista telefónica las intervenciones suelen alternar.
                role = client_label if previous_role == agent_label else agent_label
                if index == 0 and a >= c:
                    role = agent_label

            previous_role = role
            raw_words = list(segment.words or [])
            turns.append(
                {
                    "speaker": role,
                    "role": role,
                    "start": float(segment.start),
                    "end": float(segment.end),
                    "text": text,
                    "words": raw_words,
                }
            )
        return turns

    def transcribe(
        self,
        wav: Path,
        agent_label: str,
        client_label: str,
        uppercase: bool,
        language: str = "ES",
        show_timestamps: bool = True,
        progress=None,
    ) -> tuple[list[dict], str | None]:
        if progress:
            progress(8, "CARGANDO MOTOR DE TRANSCRIPCION...")

        conversation = self.asr.transcribe(
            wav,
            language=language,
            uppercase=False,
            show_timestamps=False,
            progress_callback=lambda value, message: progress(
                8 + int(max(0, min(100, value)) * 0.60), message
            ) if progress else None,
        )

        words = self._flatten_words(conversation)
        if not words:
            raise RuntimeError("EL MOTOR FINALIZO SIN TEXTO RECONOCIDO.")

        warning: str | None = None
        try:
            diar_segments = self.diar.diarize(wav, progress)
            turns = self._turns_from_diarization(words, diar_segments)
            if not turns:
                raise RuntimeError("NO FUE POSIBLE ASIGNAR PALABRAS A LOS HABLANTES.")

            role_map = infer_role_map(turns, agent_label, client_label)
            turns = refine_turn_roles(
                turns,
                role_map,
                agent_label=agent_label,
                client_label=client_label,
            )
        except Exception as exc:
            warning = str(exc).strip() or exc.__class__.__name__
            turns = self._fallback_turns(conversation, agent_label, client_label)

        out: list[dict] = []
        for turn in turns:
            label = str(turn.get("role", turn.get("speaker", "HABLANTE")))
            text = str(turn.get("text", "")).strip()
            if uppercase:
                text = text.upper()
                label = label.upper()

            start = float(turn.get("start", 0.0))
            end = float(turn.get("end", start))
            prefix = f"[{start:07.2f}] " if show_timestamps else ""
            out.append(
                {
                    "start": start,
                    "end": end,
                    "speaker": label,
                    "text": f"{prefix}{label}: {text}",
                    "words": list(turn.get("words", []) or []),
                }
            )

        if progress:
            progress(98, "TRANSCRIPCION Y ROLES LISTOS")
        return out, warning
