from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from copy import deepcopy

# -----------------------------------------------------------------------------
# Clasificador de rol V3
# -----------------------------------------------------------------------------
# SortFormer identifica huellas de voz (speaker 0 / speaker 1), pero en bordes,
# interrupciones o respuestas de 1-2 palabras puede asignar alguna frase al
# cluster equivocado. Por eso no basta con mapear speaker 0 = AGENTE y speaker
# 1 = CLIENTE una sola vez para toda la llamada.
#
# Este módulo trabaja en dos capas:
#   1) determina el mapa global de las dos voces;
#   2) revisa cada intervención y corrige SOLO contradicciones textuales fuertes.
#
# El objetivo es mantener la identidad acústica como señal principal sin dejar
# pasar errores evidentes como "BUEN DÍA, ME COMUNICO..." etiquetado CLIENTE.
# -----------------------------------------------------------------------------

AGENT_PHRASES = {
    # presentación / encuadre
    "mi nombre es": 11.0,
    "mi nombre": 7.0,
    "le habla": 10.0,
    "me comunico": 10.0,
    "me estoy comunicando": 10.0,
    "nos comunicamos": 9.0,
    "llamo de": 9.0,
    "llamamos de": 9.0,
    "pertenezco a": 9.0,
    "soy de la empresa": 8.0,
    "de la empresa ipsos": 10.0,
    "empresa ipsos": 9.0,
    "hablo con": 7.0,
    "me comunico con": 11.0,
    "tengo el gusto de hablar": 7.0,
    "buen dia me comunico": 12.0,
    "buenas tardes me comunico": 12.0,
    "buenas noches me comunico": 12.0,

    # encuesta / consentimiento
    "encuesta": 7.0,
    "entrevista": 6.0,
    "estudio": 4.0,
    "unas preguntas": 8.0,
    "algunas preguntas": 8.0,
    "responder unas preguntas": 9.0,
    "antes de continuar": 9.0,
    "para comenzar": 8.0,
    "para efecto de supervision": 10.0,
    "para efectos de supervision": 10.0,
    "esta entrevista sera grabada": 12.0,
    "seran tratadas de manera confidencial": 10.0,
    "seran tratados de manera confidencial": 10.0,

    # preguntas de estudio / NPS
    "en una escala": 10.0,
    "del uno al": 9.0,
    "del 1 al": 9.0,
    "del cero al diez": 11.0,
    "del 0 al 10": 11.0,
    "que nota": 9.0,
    "que tan probable": 10.0,
    "recomendaria": 6.0,
    "recomendaria usted": 9.0,
    "por que motivo": 8.0,
    "podria indicarme": 8.0,
    "me podria indicar": 8.0,
    "quisiera preguntarle": 8.0,
    "quisiera informarle": 8.0,
    "para finalizar": 7.0,
    "ultima pregunta": 7.0,
    "gracias por su tiempo": 9.0,
    "muchas gracias por su tiempo": 10.0,
    "que tenga buen dia": 7.0,
}

# Frases que suelen ser respuesta del entrevistado. Se usan con menor peso que
# los anclajes de agente, porque algunas también pueden aparecer al repreguntar.
CLIENT_PHRASES = {
    "alo": 5.0,
    "si diga": 5.0,
    "digame": 4.0,
    "con el": 5.0,
    "con el señorita": 7.0,
    "soy yo": 6.0,
    "yo mismo": 6.0,
    "tengo varios": 7.0,
    "tengo varios seguros": 10.0,
    "de que seguro": 7.0,
    "no se": 5.0,
    "no recuerdo": 5.0,
    "no lo ocupo": 6.0,
    "no lo uso": 6.0,
    "por el precio": 7.0,
    "me atendieron": 5.0,
    "tuve problemas": 6.0,
    "no me gusto": 5.0,
    "no me gustó": 5.0,
}

CLIENT_SHORT = {
    "si", "sí", "no", "claro", "correcto", "exacto", "bien", "mal",
    "bueno", "malo", "uno", "dos", "tres", "cuatro", "cinco", "seis",
    "siete", "ocho", "nueve", "diez", "alo", "aló", "diga", "digame",
    "dígame", "soy yo", "yo", "con el", "con él",
}

QUESTION_STARTS = (
    "que ", "qué ", "cual ", "cuál ", "como ", "cómo ", "cuando ",
    "cuándo ", "donde ", "dónde ", "por que ", "por qué ", "podria ",
    "podría ", "me podria ", "me podría ", "usted ", "considera ",
    "recomendaria ", "recomendaría ", "evaluaria ", "evaluaría ",
    "tiene tiempo", "tiene usted", "recuerda ", "ha utilizado ",
)

# Anclajes que permiten partir una intervención mezclada. Ejemplo real:
# "CON ÉL, SEÑORITA. MI NOMBRE ES LORETO..."
MIXED_AGENT_ANCHORS = (
    "mi nombre es",
    "le habla",
    "me comunico",
    "me estoy comunicando",
    "pertenezco a",
    "antes de continuar",
    "para comenzar",
)


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text).lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    # elimina etiquetas residuales del motor, por ejemplo <ES-ES>
    text = re.sub(r"<[^>]{1,32}>", " ", text)
    text = re.sub(r"[^a-z0-9¿? ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _looks_like_question(text: str) -> bool:
    original = str(text)
    normalized = _norm(original)
    if "?" in original or "¿" in original:
        return True
    return any(normalized.startswith(_norm(prefix)) for prefix in QUESTION_STARTS)


def _looks_like_numeric_answer(text: str) -> bool:
    normalized = _norm(text)
    if normalized in CLIENT_SHORT:
        return True
    if re.fullmatch(r"(?:un\s+)?(?:[0-9]|10)", normalized):
        return True
    if re.fullmatch(
        r"(?:le\s+)?(?:pongo|doy|daria|daría)\s+(?:un\s+)?"
        r"(?:[0-9]|10|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez)",
        normalized,
    ):
        return True
    return False


def score_role_text(text: str) -> tuple[float, float]:
    """Devuelve (puntaje_agente, puntaje_cliente) para una intervención."""
    original = str(text or "")
    normalized = _norm(original)
    words = normalized.split()

    if not words:
        return 0.0, 0.0

    agent = 0.0
    client = 0.0

    for phrase, weight in AGENT_PHRASES.items():
        if _norm(phrase) in normalized:
            agent += weight

    for phrase, weight in CLIENT_PHRASES.items():
        if _norm(phrase) in normalized:
            client += weight

    is_question = _looks_like_question(original)
    if is_question:
        agent += 3.5

    if len(words) <= 4 and normalized in {_norm(x) for x in CLIENT_SHORT}:
        client += 7.0

    if _looks_like_numeric_answer(original):
        client += 8.0

    # Respuesta causal típica del cliente. Solo aplica si no hay anclaje claro
    # de cuestionario/agente en la misma intervención.
    if normalized.startswith("porque ") and agent < 5.0:
        client += 3.0

    # Primera persona con experiencia/posesión suele ser respuesta del cliente.
    if agent < 5.0 and re.search(
        r"\b(?:yo|tengo|tuve|uso|ocupo|contrate|contraté|pague|pagué|me atendieron)\b",
        normalized,
    ):
        client += 2.0

    # Una intervención larga y estructurada tiene una leve inclinación al agente,
    # pero nunca debe superar por sí sola las señales textuales.
    if len(words) >= 18:
        agent += min(2.5, len(words) / 24.0)

    return agent, client


def infer_role_map(
    utterances: list[dict],
    agent_label: str = "AGENTE",
    client_label: str = "CLIENTE",
) -> dict[str, str]:
    """Determina qué cluster acústico corresponde globalmente a cada rol."""
    speakers: list[str] = []
    for utterance in utterances:
        speaker = str(utterance.get("speaker", ""))
        if speaker and speaker not in speakers:
            speakers.append(speaker)

    if not speakers:
        return {}
    if len(speakers) == 1:
        return {speakers[0]: agent_label}

    speakers = speakers[:2]
    score = defaultdict(float)
    stats = defaultdict(lambda: {"turns": 0, "words": 0, "questions": 0, "short": 0})

    for utterance in utterances:
        speaker = str(utterance.get("speaker", ""))
        if speaker not in speakers:
            continue

        text = str(utterance.get("text", ""))
        normalized = _norm(text)
        words = normalized.split()
        agent_score, client_score = score_role_text(text)

        score[speaker] += agent_score - client_score
        stats[speaker]["turns"] += 1
        stats[speaker]["words"] += len(words)

        if _looks_like_question(text):
            stats[speaker]["questions"] += 1
        if len(words) <= 4 and not _looks_like_question(text):
            stats[speaker]["short"] += 1

    for speaker in speakers:
        st = stats[speaker]
        turns = max(1, st["turns"])
        question_ratio = st["questions"] / turns
        short_ratio = st["short"] / turns
        avg_words = st["words"] / turns

        score[speaker] += question_ratio * 8.0
        score[speaker] -= short_ratio * 3.0
        score[speaker] += min(2.0, avg_words / 12.0)

    agent_speaker = max(speakers, key=lambda s: score[s])
    client_speaker = speakers[1] if speakers[0] == agent_speaker else speakers[0]
    return {agent_speaker: agent_label, client_speaker: client_label}


def _word_tokens(words: list[dict]) -> list[str]:
    tokens: list[str] = []
    for word in words:
        token = _norm(str(word.get("text", "")))
        if token:
            # La salida por palabra normalmente trae una palabra, pero toleramos
            # tokens con más de una por compatibilidad.
            tokens.extend(token.split())
    return tokens


def _find_phrase_index(tokens: list[str], phrase: str) -> int | None:
    wanted = _norm(phrase).split()
    if not wanted or len(tokens) < len(wanted):
        return None
    for index in range(0, len(tokens) - len(wanted) + 1):
        if tokens[index:index + len(wanted)] == wanted:
            return index
    return None


def _split_mixed_turn(turn: dict) -> list[dict]:
    """
    Parte únicamente mezclas de alta confianza CLIENTE -> AGENTE.

    No intenta cortar frases normales. Solo actúa cuando aparece un anclaje de
    presentación muy fuerte después de un prefijo muy corto típico del cliente.
    """
    words = list(turn.get("words", []) or [])
    if len(words) < 4:
        return [turn]

    # Para poder mapear con precisión índice de token -> índice de word, cada
    # elemento se normaliza a una palabra lógica. Si un elemento contiene varias,
    # se evita partir para no introducir timestamps falsos.
    normalized_words = [_norm(str(w.get("text", ""))) for w in words]
    if any(len(item.split()) != 1 for item in normalized_words if item):
        return [turn]

    tokens = [item for item in normalized_words if item]
    if len(tokens) != len(words):
        return [turn]

    best_index: int | None = None
    for anchor in MIXED_AGENT_ANCHORS:
        idx = _find_phrase_index(tokens, anchor)
        if idx is not None and 1 <= idx <= 6:
            if best_index is None or idx < best_index:
                best_index = idx

    if best_index is None:
        return [turn]

    prefix_words = words[:best_index]
    suffix_words = words[best_index:]
    prefix_text = " ".join(str(w.get("text", "")).strip() for w in prefix_words).strip()
    prefix_norm = _norm(prefix_text)

    # El prefijo debe parecer una contestación corta/confirmación del cliente.
    prefix_client_markers = (
        "si", "sí", "claro", "correcto", "con el", "con él", "soy yo",
        "yo", "digame", "dígame", "señorita", "senorita", "señor", "senor",
        "bueno", "ya",
    )
    if len(prefix_norm.split()) > 6 or not any(_norm(x) in prefix_norm for x in prefix_client_markers):
        return [turn]

    first = deepcopy(turn)
    second = deepcopy(turn)

    first["words"] = prefix_words
    first["text"] = prefix_text
    first["start"] = float(prefix_words[0].get("start", turn.get("start", 0.0)))
    first["end"] = float(prefix_words[-1].get("end", first["start"]))
    first["forced_role"] = "CLIENTE"

    second["words"] = suffix_words
    second["text"] = " ".join(str(w.get("text", "")).strip() for w in suffix_words).strip()
    second["start"] = float(suffix_words[0].get("start", turn.get("start", 0.0)))
    second["end"] = float(suffix_words[-1].get("end", second["start"]))
    second["forced_role"] = "AGENTE"

    return [first, second]


def refine_turn_roles(
    turns: list[dict],
    role_map: dict[str, str],
    agent_label: str = "AGENTE",
    client_label: str = "CLIENTE",
) -> list[dict]:
    """
    Corrige errores locales de speaker sin destruir la diarización completa.

    Regla principal:
      - el speaker acústico sigue mandando;
      - una frase se cambia de rol únicamente cuando la evidencia textual es
        fuerte y contradictoria con el mapa acústico.
    """
    expanded: list[dict] = []
    for original in turns:
        expanded.extend(_split_mixed_turn(deepcopy(original)))

    result: list[dict] = []

    for turn in expanded:
        raw_speaker = str(turn.get("speaker", ""))
        base_label = role_map.get(raw_speaker, agent_label)

        # Split de mezcla de alta confianza.
        forced = str(turn.pop("forced_role", "") or "").upper()
        if forced == "AGENTE":
            label = agent_label
        elif forced == "CLIENTE":
            label = client_label
        else:
            agent_score, client_score = score_role_text(str(turn.get("text", "")))
            margin = agent_score - client_score

            label = base_label

            # Overrides conservadores. Evitan cambiar respuestas dudosas, pero
            # corrigen anclajes inequívocos del protocolo de encuesta.
            if base_label == client_label:
                if agent_score >= 8.0 and margin >= 5.0:
                    label = agent_label
            elif base_label == agent_label:
                if client_score >= 8.0 and margin <= -5.0:
                    label = client_label

            # Respuestas ultracortas tienen prioridad aun cuando el borde de
            # SortFormer las haya pegado al turno del agente.
            normalized = _norm(str(turn.get("text", "")))
            if _looks_like_numeric_answer(normalized) and len(normalized.split()) <= 5:
                label = client_label

        turn["role"] = label
        result.append(turn)

    return result
