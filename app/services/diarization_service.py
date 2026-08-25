from __future__ import annotations

import logging
import os
import re
import threading
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path


from app.models.conversation import Conversation, Segment
from app.services.paths_service import AppPaths
from app.services.speaker_rescue_service import SpeakerRescueService


@dataclass(frozen=True)
class SpeakerTurn:
    start: float
    end: float
    speaker: str

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


@dataclass
class AlignedWord:
    start: float
    end: float
    text: str
    raw_speaker: str
    probability: float = 0.0

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


@dataclass
class RawUtterance:
    raw_speaker: str
    words: list[AlignedWord] = field(default_factory=list)

    @property
    def start(self) -> float:
        return self.words[0].start if self.words else 0.0

    @property
    def end(self) -> float:
        return self.words[-1].end if self.words else self.start

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)

    @property
    def text(self) -> str:
        return DiarizationService._join_word_text(
            [word.text for word in self.words]
        )


class DiarizationService:
    """
    Speaker V2.

    pyannote Community-1 decide identidad acústica (voz A / voz B).
    Whisper aporta tiempos por palabra.
    Este servicio reconcilia ambos resultados y recién después determina
    qué voz corresponde a AGENTE y cuál a CLIENTE.

    Se evita asumir que la primera persona que habla es el agente.
    """

    MODEL_FOLDER = "pyannote-community-1"
    REQUIRED_MARKERS = (
        "config.yaml",
    )

    _pipeline = None
    _pipeline_lock = threading.RLock()

    # Frases con alta señal de rol AGENTE en encuestas / entrevistas.
    _AGENT_PHRASES = {
        "mi nombre es": 7.0,
        "le habla": 7.0,
        "mi nombre": 5.0,
        "me comunico": 5.0,
        "me estoy comunicando": 5.0,
        "hablo con": 4.0,
        "tengo el gusto de hablar": 4.0,
        "llamo de": 5.0,
        "llamamos de": 5.0,
        "encuesta": 5.0,
        "entrevista": 4.0,
        "unas preguntas": 5.0,
        "algunas preguntas": 5.0,
        "en una escala": 6.0,
        "del 1 al": 6.0,
        "del uno al": 6.0,
        "que nota": 6.0,
        "qué nota": 6.0,
        "por que motivo": 4.0,
        "por qué motivo": 4.0,
        "podria indicarme": 4.0,
        "podría indicarme": 4.0,
        "me podria indicar": 4.0,
        "me podría indicar": 4.0,
        "para finalizar": 4.0,
        "ultima pregunta": 4.0,
        "última pregunta": 4.0,
        "muchas gracias por su tiempo": 6.0,
        "gracias por su tiempo": 5.0,
        "que tenga buen dia": 4.0,
        "que tenga buen día": 4.0,
    }

    _QUESTION_STARTS = (
        "que ",
        "qué ",
        "cual ",
        "cuál ",
        "como ",
        "cómo ",
        "cuando ",
        "cuándo ",
        "donde ",
        "dónde ",
        "por que ",
        "por qué ",
        "podria ",
        "podría ",
        "me podria ",
        "me podría ",
        "usted ",
        "considera ",
        "recomendaria ",
        "recomendaría ",
        "evaluaria ",
        "evaluaría ",
    )

    _CLIENT_PHRASES = {
        "alo": 4.0,
        "aló": 4.0,
        "si diga": 4.0,
        "sí diga": 4.0,
        "digame": 3.0,
        "dígame": 3.0,
        "me atendieron": 3.0,
        "tuve problemas": 4.0,
        "no me gusto": 3.0,
        "no me gustó": 3.0,
        "porque": 1.5,
    }

    _SHORT_CLIENT_ANSWERS = {
        "si",
        "sí",
        "no",
        "claro",
        "correcto",
        "exacto",
        "bien",
        "mal",
        "bueno",
        "malo",
        "uno",
        "dos",
        "tres",
        "cuatro",
        "cinco",
        "seis",
        "siete",
        "ocho",
        "nueve",
        "diez",
    }

    def __init__(self) -> None:
        self._paths = AppPaths()
        self._logger = logging.getLogger(__name__)
        self._rescue = SpeakerRescueService()

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
            "IDENTIFICADOR DE VOCES V2: LISTO"
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
                "CARGANDO IDENTIFICADOR DE VOCES V2...",
            )

        pipeline = self._load_pipeline()

        if progress_callback:
            progress_callback(
                92,
                "SEPARANDO DOS VOCES...",
            )

        import torch
        import torchaudio

        progress_hook = self._make_progress_hook(progress_callback)
        waveform, sample_rate = torchaudio.load(str(audio_path))
        if waveform.ndim == 2 and waveform.shape[0] > 1:
            waveform = waveform.mean(dim=0, keepdim=True)

        with torch.inference_mode():
            result = pipeline(
                {
                    "waveform": waveform,
                    "sample_rate": int(sample_rate),
                },
                num_speakers=2,
                hook=progress_hook,
            )

        # Community-1 ofrece una salida exclusiva pensada expresamente
        # para reconciliar diarización con transcripción.
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

        unique_speakers = sorted({turn.speaker for turn in turns})

        if self._needs_rescue(turns, unique_speakers):
            if progress_callback:
                progress_callback(94, "SEPARACIÓN DUDOSA · ACTIVANDO SEGUNDA CAPA...")
            try:
                rescue_turns = self._rescue.recover_two_speakers(
                    conversation=conversation,
                    audio_path=audio_path,
                    progress_callback=progress_callback,
                )
                turns = [
                    SpeakerTurn(
                        start=float(item.start),
                        end=float(item.end),
                        speaker=str(item.speaker),
                    )
                    for item in rescue_turns
                ]
                unique_speakers = sorted({turn.speaker for turn in turns})
                self._logger.warning("LOCAL PRO: ECAPA RESCUE ACTIVADO")
            except Exception:
                self._logger.exception("ECAPA RESCUE NO PUDO RECUPERAR DOS VOCES")

        if len(unique_speakers) != 2:
            raise RuntimeError(
                "NO FUE POSIBLE ESTABLECER DOS HABLANTES CON LAS DOS CAPAS LOCALES."
            )

        if progress_callback:
            progress_callback(
                95,
                "ALINEANDO PALABRAS CON CADA VOZ...",
            )

        show_timestamps = self._conversation_has_timestamps(
            conversation
        )

        aligned_words = self._align_conversation_words(
            conversation,
            turns,
        )

        if not aligned_words:
            # Compatibilidad defensiva con cualquier motor que todavía no
            # entregue palabras: se usa un bloque por segmento.
            aligned_words = self._fallback_segment_alignment(
                conversation,
                turns,
            )

        # Corrige micro cambios aislados típicos de límites acústicos.
        aligned_words = self._smooth_isolated_word_flips(
            aligned_words
        )

        raw_utterances = self._group_words_into_utterances(
            aligned_words
        )

        if not raw_utterances:
            raise RuntimeError(
                "NO FUE POSIBLE RECONSTRUIR LOS TURNOS "
                "DE AGENTE Y CLIENTE."
            )

        if progress_callback:
            progress_callback(
                97,
                "DETERMINANDO QUIÉN ES AGENTE Y QUIÉN ES CLIENTE...",
            )

        speaker_map = self._infer_speaker_map(
            raw_utterances=raw_utterances,
            unique_speakers=unique_speakers,
            speaker_one_label=speaker_one_label,
            speaker_two_label=speaker_two_label,
            first_speaker_is_one=first_speaker_is_one,
        )

        rebuilt_segments = self._build_final_segments(
            raw_utterances,
            speaker_map,
            show_timestamps,
        )

        # Reemplaza los segmentos originales: ahora un bloque Whisper puede
        # transformarse en dos o más intervenciones si hubo cambio de voz.
        conversation.segments = rebuilt_segments

        if progress_callback:
            progress_callback(
                99,
                "AGENTE Y CLIENTE IDENTIFICADOS · SPEAKER V2",
            )

        return conversation

    def _load_pipeline(self):
        with self._pipeline_lock:
            if self.__class__._pipeline is not None:
                return self.__class__._pipeline

            # El modelo es local. Desactivar telemetría evita esperas de red
            # innecesarias en equipos sin Internet o con firewall.
            os.environ.setdefault(
                "PYANNOTE_METRICS_ENABLED",
                "0",
            )
            os.environ.setdefault(
                "HF_HUB_DISABLE_TELEMETRY",
                "1",
            )
            os.environ.setdefault(
                "HF_HUB_OFFLINE",
                "1",
            )

            import torch
            from pyannote.audio import Pipeline

            available = max(
                1,
                os.cpu_count() or 2,
            )

            # Community-1 es pesado en CPU. Se dejan suficientes hilos para
            # acelerar la inferencia sin bloquear completamente Windows.
            torch.set_num_threads(
                max(
                    2,
                    min(4, available - 2),
                )
            )

            try:
                torch.set_num_interop_threads(1)
            except RuntimeError:
                pass

            pipeline = Pipeline.from_pretrained(
                str(self.model_path)
            )

            pipeline.to(
                torch.device("cpu")
            )

            # En pyannote 4.x ambos tamaños por defecto son 1.
            # Un batch moderado reduce el tiempo de segmentación/embeddings
            # en CPU sin disparar el uso de memoria.
            try:
                pipeline.segmentation_batch_size = 2
            except Exception:
                pass

            try:
                pipeline.embedding_batch_size = 4
            except Exception:
                pass

            self.__class__._pipeline = pipeline
            return pipeline



    @staticmethod
    def _needs_rescue(
        turns: list[SpeakerTurn],
        unique_speakers: list[str],
    ) -> bool:
        if len(unique_speakers) != 2:
            return True

        coverage = {speaker: 0.0 for speaker in unique_speakers}
        counts = {speaker: 0 for speaker in unique_speakers}
        for turn in turns:
            coverage[turn.speaker] = coverage.get(turn.speaker, 0.0) + turn.duration
            counts[turn.speaker] = counts.get(turn.speaker, 0) + 1

        total = sum(coverage.values())
        if total <= 0:
            return True

        minority = min(coverage.values())
        minority_count = min(counts.values())

        return (
            minority < 0.80
            or minority / total < 0.015
            or (minority_count <= 1 and minority < 1.6)
        )

    def _make_progress_hook(
        self,
        progress_callback,
    ):
        """
        Traduce el progreso interno de Community-1 al progreso visible
        de la aplicación. Antes la UI permanecía clavada en
        "SEPARANDO DOS VOCES..." durante toda la inferencia.
        """
        if progress_callback is None:
            return None

        last_value = {"value": 92}

        stage_ranges = {
            "segmentation": (92, 95, "ANALIZANDO CAMBIOS DE VOZ"),
            "speaker_counting": (95, 95, "CONTANDO PARTICIPANTES"),
            "embeddings": (95, 98, "COMPARANDO IDENTIDAD DE VOCES"),
            "discrete_diarization": (98, 98, "RECONSTRUYENDO TURNOS"),
        }

        def hook(
            step_name,
            step_artifact=None,
            *,
            file=None,
            completed=None,
            total=None,
            **kwargs,
        ):
            start, end, label = stage_ranges.get(
                str(step_name),
                (
                    last_value["value"],
                    min(98, last_value["value"] + 1),
                    "SEPARANDO VOCES",
                ),
            )

            value = start

            if (
                completed is not None
                and total not in (None, 0)
            ):
                try:
                    ratio = max(
                        0.0,
                        min(
                            1.0,
                            float(completed) / float(total),
                        ),
                    )
                    value = int(
                        round(
                            start
                            + (end - start) * ratio
                        )
                    )
                    label = (
                        f"{label}... "
                        f"{int(ratio * 100)} %"
                    )
                except Exception:
                    value = start

            value = max(
                last_value["value"],
                min(98, value),
            )
            last_value["value"] = value

            try:
                progress_callback(
                    value,
                    label,
                )
            except Exception:
                pass

            self._logger.debug(
                "PYANNOTE STEP=%s completed=%s total=%s",
                step_name,
                completed,
                total,
            )

        return hook

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

    def _align_conversation_words(
        self,
        conversation: Conversation,
        turns: list[SpeakerTurn],
    ) -> list[AlignedWord]:
        rows: list[AlignedWord] = []

        for segment in conversation.segments:
            for word in (getattr(segment, "words", None) or []):
                text = str(word.get("text", "") or "")
                if not text.strip():
                    continue

                start = float(
                    word.get("start", segment.start)
                )
                end = float(
                    word.get("end", segment.end)
                )

                raw_speaker = self._speaker_for_word(
                    start,
                    end,
                    turns,
                )

                rows.append(
                    AlignedWord(
                        start=start,
                        end=end,
                        text=text,
                        raw_speaker=raw_speaker,
                        probability=float(
                            word.get("probability", 0.0) or 0.0
                        ),
                    )
                )

        return sorted(
            rows,
            key=lambda word: (
                word.start,
                word.end,
            ),
        )

    def _fallback_segment_alignment(
        self,
        conversation: Conversation,
        turns: list[SpeakerTurn],
    ) -> list[AlignedWord]:
        rows = []

        for segment in conversation.segments:
            raw_speaker, _ = self._best_speaker(
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

            body = self._strip_timestamp_and_label(
                segment.text
            )

            rows.append(
                AlignedWord(
                    start=float(segment.start),
                    end=float(segment.end),
                    text=body,
                    raw_speaker=raw_speaker,
                    probability=float(
                        segment.confidence or 0.0
                    ),
                )
            )

        return rows

    def _speaker_for_word(
        self,
        start: float,
        end: float,
        turns: list[SpeakerTurn],
    ) -> str:
        """
        Con exclusive diarization, el punto medio de la palabra suele ser la
        referencia más estable. Si cae en un hueco, usa solapamiento y luego
        el turno temporalmente más cercano.
        """
        midpoint = (start + end) / 2.0

        containing = [
            turn
            for turn in turns
            if turn.start <= midpoint <= turn.end
        ]

        if containing:
            if len(containing) == 1:
                return containing[0].speaker

            return max(
                containing,
                key=lambda turn: self._overlap(
                    start,
                    end,
                    turn.start,
                    turn.end,
                ),
            ).speaker

        raw_speaker, confidence = self._best_speaker(
            start,
            end,
            turns,
        )

        if raw_speaker is not None and confidence > 0:
            return raw_speaker

        return self._nearest_speaker(
            start,
            end,
            turns,
        )

    @staticmethod
    def _overlap(
        start_a: float,
        end_a: float,
        start_b: float,
        end_b: float,
    ) -> float:
        return max(
            0.0,
            min(end_a, end_b) - max(start_a, start_b),
        )

    @classmethod
    def _smooth_isolated_word_flips(
        cls,
        words: list[AlignedWord],
    ) -> list[AlignedWord]:
        """
        Corrige únicamente micro-islas muy conservadoras:
        A / B(una palabra muy corta) / A.
        No fuerza alternancia ni cambia respuestas normales.
        """
        if len(words) < 3:
            return words

        result = list(words)

        for index in range(1, len(result) - 1):
            previous = result[index - 1]
            current = result[index]
            following = result[index + 1]

            if previous.raw_speaker != following.raw_speaker:
                continue

            if current.raw_speaker == previous.raw_speaker:
                continue

            token = cls._normalize(current.text)

            # Solo palabras muy cortas no informativas. Nunca corrige
            # sí/no/notas porque esas sí pueden ser respuestas del cliente.
            protected = {
                "si", "sí", "no",
                "uno", "dos", "tres", "cuatro", "cinco",
                "seis", "siete", "ocho", "nueve", "diez",
                "1", "2", "3", "4", "5", "6", "7", "8", "9", "10",
            }

            if token in protected:
                continue

            if (
                current.duration <= 0.55
                and len(token.split()) <= 1
                and current.start - previous.end <= 0.25
                and following.start - current.end <= 0.25
            ):
                result[index] = AlignedWord(
                    start=current.start,
                    end=current.end,
                    text=current.text,
                    raw_speaker=previous.raw_speaker,
                    probability=current.probability,
                )

        return result

    @classmethod
    def _group_words_into_utterances(
        cls,
        words: list[AlignedWord],
    ) -> list[RawUtterance]:
        if not words:
            return []

        groups: list[RawUtterance] = []

        for word in words:
            if not groups:
                groups.append(
                    RawUtterance(
                        raw_speaker=word.raw_speaker,
                        words=[word],
                    )
                )
                continue

            current = groups[-1]
            gap = max(0.0, word.start - current.end)

            # Un turno continuo del mismo participante puede incluir una pausa
            # breve. Pausas mayores se conservan como nueva intervención.
            if (
                current.raw_speaker == word.raw_speaker
                and gap <= 1.35
            ):
                current.words.append(word)
            else:
                groups.append(
                    RawUtterance(
                        raw_speaker=word.raw_speaker,
                        words=[word],
                    )
                )

        return groups

    def _infer_speaker_map(
        self,
        raw_utterances: list[RawUtterance],
        unique_speakers: list[str],
        speaker_one_label: str,
        speaker_two_label: str,
        first_speaker_is_one: bool,
    ) -> dict[str, str]:
        """
        Determina el rol por estructura de conversación y no por orden de
        aparición. Se activa cuando las etiquetas configuradas representan
        claramente AGENTE / CLIENTE. En etiquetas personalizadas conserva
        la configuración histórica como fallback.
        """
        role_labels = self._resolve_role_labels(
            speaker_one_label,
            speaker_two_label,
        )

        if role_labels is None:
            return self._legacy_fallback_map(
                raw_utterances,
                unique_speakers,
                speaker_one_label,
                speaker_two_label,
                first_speaker_is_one,
            )

        agent_label, client_label = role_labels

        by_speaker: dict[str, list[RawUtterance]] = {
            speaker: []
            for speaker in unique_speakers
        }

        for utterance in raw_utterances:
            by_speaker.setdefault(
                utterance.raw_speaker,
                [],
            ).append(utterance)

        scores = {
            speaker: self._role_score(
                utterances
            )
            for speaker, utterances in by_speaker.items()
        }

        ordered = sorted(
            scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        best_speaker, best_score = ordered[0]
        second_speaker, second_score = ordered[1]

        delta = best_score - second_score

        self._logger.info(
            "SPEAKER V2 ROLE SCORE %s=%.2f / %s=%.2f / delta=%.2f",
            best_speaker,
            best_score,
            second_speaker,
            second_score,
            delta,
        )

        # Con diferencia suficiente se usa clasificación contextual.
        # Si el texto no entrega señal clara se conserva el control manual
        # "primer hablante" como red de seguridad, no como regla principal.
        if delta >= 3.0:
            return {
                best_speaker: agent_label,
                second_speaker: client_label,
            }

        self._logger.warning(
            "SPEAKER V2: rol textual ambiguo; usando configuración "
            "de primer hablante como fallback."
        )

        return self._legacy_fallback_map(
            raw_utterances,
            unique_speakers,
            speaker_one_label,
            speaker_two_label,
            first_speaker_is_one,
        )

    @classmethod
    def _role_score(
        cls,
        utterances: list[RawUtterance],
    ) -> float:
        if not utterances:
            return -100.0

        score = 0.0
        question_turns = 0
        short_answer_turns = 0
        numeric_answer_turns = 0
        total_words = 0

        for utterance in utterances:
            text_original = utterance.text.strip()
            text = cls._normalize(text_original)
            words = text.split()
            total_words += len(words)

            for phrase, weight in cls._AGENT_PHRASES.items():
                if cls._normalize(phrase) in text:
                    score += weight

            for phrase, weight in cls._CLIENT_PHRASES.items():
                if cls._normalize(phrase) in text:
                    score -= weight

            is_question = cls._looks_like_question(
                text_original,
                text,
            )

            if is_question:
                question_turns += 1
                score += 2.8

            if (
                0 < len(words) <= 4
                and not is_question
            ):
                short_answer_turns += 1

            if cls._looks_like_numeric_answer(text):
                numeric_answer_turns += 1

        turn_count = max(1, len(utterances))

        question_ratio = question_turns / turn_count
        short_ratio = short_answer_turns / turn_count
        numeric_ratio = numeric_answer_turns / turn_count

        score += question_ratio * 14.0
        score -= short_ratio * 5.0
        score -= numeric_ratio * 7.0

        # Un agente normalmente conduce la entrevista con más texto
        # estructurado. Peso bajo para no sesgar entrevistas abiertas.
        average_words = total_words / turn_count
        score += min(3.0, average_words / 8.0)

        return score

    @classmethod
    def _looks_like_question(
        cls,
        original: str,
        normalized: str,
    ) -> bool:
        if "?" in original or "¿" in original:
            return True

        normalized = normalized.strip()

        return any(
            normalized.startswith(
                cls._normalize(prefix)
            )
            for prefix in cls._QUESTION_STARTS
        )

    @classmethod
    def _looks_like_numeric_answer(
        cls,
        normalized: str,
    ) -> bool:
        text = normalized.strip()

        if text in cls._SHORT_CLIENT_ANSWERS:
            return True

        if re.fullmatch(
            r"(?:un\s+)?(?:[0-9]|10)",
            text,
        ):
            return True

        if re.fullmatch(
            r"(?:le\s+)?(?:pongo|doy|daria|daría)\s+"
            r"(?:un\s+)?(?:[0-9]|10|uno|dos|tres|cuatro|cinco|"
            r"seis|siete|ocho|nueve|diez)",
            text,
        ):
            return True

        return False

    @classmethod
    def _resolve_role_labels(
        cls,
        label_one: str,
        label_two: str,
    ) -> tuple[str, str] | None:
        one = cls._normalize(label_one)
        two = cls._normalize(label_two)

        agent_terms = (
            "agente",
            "ejecutivo",
            "asesor",
            "encuestador",
            "operador",
        )

        client_terms = (
            "cliente",
            "usuario",
            "entrevistado",
            "peb",
        )

        one_agent = any(term in one for term in agent_terms)
        two_agent = any(term in two for term in agent_terms)
        one_client = any(term in one for term in client_terms)
        two_client = any(term in two for term in client_terms)

        if one_agent and two_client:
            return label_one, label_two

        if two_agent and one_client:
            return label_two, label_one

        # Si solo una etiqueta declara el rol, inferimos la otra.
        if one_agent and not two_agent:
            return label_one, label_two

        if two_agent and not one_agent:
            return label_two, label_one

        if one_client and not two_client:
            return label_two, label_one

        if two_client and not one_client:
            return label_one, label_two

        return None

    @staticmethod
    def _legacy_fallback_map(
        raw_utterances: list[RawUtterance],
        unique_speakers: list[str],
        speaker_one_label: str,
        speaker_two_label: str,
        first_speaker_is_one: bool,
    ) -> dict[str, str]:
        first_speaker = (
            raw_utterances[0].raw_speaker
            if raw_utterances
            else unique_speakers[0]
        )

        other_speaker = next(
            speaker
            for speaker in unique_speakers
            if speaker != first_speaker
        )

        if first_speaker_is_one:
            return {
                first_speaker: speaker_one_label,
                other_speaker: speaker_two_label,
            }

        return {
            first_speaker: speaker_two_label,
            other_speaker: speaker_one_label,
        }

    def _build_final_segments(
        self,
        utterances: list[RawUtterance],
        speaker_map: dict[str, str],
        show_timestamps: bool,
    ) -> list[Segment]:
        segments: list[Segment] = []

        for utterance in utterances:
            if not utterance.words:
                continue

            label = speaker_map[
                utterance.raw_speaker
            ]

            body = utterance.text.strip()

            if not body:
                continue

            if show_timestamps:
                text = (
                    f"[{self._format_time(utterance.start)} - "
                    f"{self._format_time(utterance.end)}] "
                    f"{label}: {body}"
                )
            else:
                text = f"{label}: {body}"

            probabilities = [
                word.probability
                for word in utterance.words
                if word.probability > 0
            ]

            confidence = (
                sum(probabilities) / len(probabilities)
                if probabilities
                else None
            )

            segments.append(
                Segment(
                    start=utterance.start,
                    end=utterance.end,
                    text=text,
                    speaker=label,
                    confidence=confidence,
                    words=[
                        {
                            "start": word.start,
                            "end": word.end,
                            "text": word.text,
                            "probability": word.probability,
                        }
                        for word in utterance.words
                    ],
                )
            )

        return segments

    @staticmethod
    def _conversation_has_timestamps(
        conversation: Conversation,
    ) -> bool:
        return any(
            re.match(
                r"^\[[^\]]+\]\s*",
                segment.text or "",
            )
            for segment in conversation.segments
        )

    @classmethod
    def _strip_timestamp_and_label(
        cls,
        text: str,
    ) -> str:
        body = re.sub(
            r"^\s*\[[^\]]+\]\s*",
            "",
            text or "",
            count=1,
        )

        body = re.sub(
            r"^\s*[^:\n]{1,40}:\s*",
            "",
            body,
            count=1,
        )

        return body.strip()

    @staticmethod
    def _join_word_text(
        pieces: list[str],
    ) -> str:
        if not pieces:
            return ""

        # faster-whisper suele conservar espacio inicial en cada token.
        direct = "".join(pieces).strip()

        # Si por algún modelo los tokens vienen sin espacios, reconstruirlos.
        if (
            len(pieces) > 1
            and " " not in direct
            and not any(
                str(piece).startswith(" ")
                for piece in pieces[1:]
            )
        ):
            direct = " ".join(
                str(piece).strip()
                for piece in pieces
            )

        direct = re.sub(
            r"\s+([,.;:!?])",
            r"\1",
            direct,
        )

        direct = re.sub(
            r"([¿¡])\s+",
            r"\1",
            direct,
        )

        direct = re.sub(
            r"\s+",
            " ",
            direct,
        ).strip()

        return direct

    @staticmethod
    def _normalize(
        text: str,
    ) -> str:
        value = (
            text or ""
        ).casefold()

        value = unicodedata.normalize(
            "NFD",
            value,
        )

        value = "".join(
            char
            for char in value
            if unicodedata.category(char) != "Mn"
        )

        value = re.sub(
            r"[^a-z0-9ñ\s]",
            " ",
            value,
        )

        value = re.sub(
            r"\s+",
            " ",
            value,
        )

        return value.strip()

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
    def _format_time(
        seconds: float,
    ) -> str:
        total = max(
            0,
            int(seconds),
        )

        minutes, secs = divmod(
            total,
            60,
        )

        hours, minutes = divmod(
            minutes,
            60,
        )

        if hours:
            return (
                f"{hours:02d}:"
                f"{minutes:02d}:"
                f"{secs:02d}"
            )

        return (
            f"{minutes:02d}:"
            f"{secs:02d}"
        )

    @classmethod
    def release(cls) -> None:
        with cls._pipeline_lock:
            cls._pipeline = None
