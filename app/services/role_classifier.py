from __future__ import annotations
import re
import unicodedata
from collections import defaultdict

AGENT_PHRASES = {
    "mi nombre es": 8.0, "le habla": 8.0, "me comunico": 6.0,
    "llamo de": 6.0, "llamamos de": 6.0, "encuesta": 5.0,
    "entrevista": 4.0, "unas preguntas": 5.0, "algunas preguntas": 5.0,
    "en una escala": 7.0, "del uno al": 7.0, "del 1 al": 7.0,
    "que nota": 6.0, "por que motivo": 5.0, "podria indicarme": 5.0,
    "me podria indicar": 5.0, "para finalizar": 4.0,
    "ultima pregunta": 4.0, "gracias por su tiempo": 6.0,
    "muchas gracias": 4.0,
}
CLIENT_SHORT = {
    "si", "no", "claro", "correcto", "exacto", "bien", "mal",
    "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete",
    "ocho", "nueve", "diez", "alo", "diga", "digame",
}
QUESTION_WORDS = ("que ", "cual ", "como ", "cuando ", "donde ", "por que ", "podria ", "usted ")


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9¿?áéíóúñ ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def infer_role_map(utterances: list[dict], agent_label='AGENTE', client_label='CLIENTE') -> dict[str,str]:
    speakers=[]
    for u in utterances:
        s=str(u.get('speaker',''))
        if s and s not in speakers: speakers.append(s)
    if len(speakers) < 2:
        return {speakers[0]: agent_label} if speakers else {}
    speakers=speakers[:2]
    score=defaultdict(float)
    stats=defaultdict(lambda: {'turns':0,'words':0,'short':0,'questions':0})
    for u in utterances:
        s=str(u.get('speaker',''))
        if s not in speakers: continue
        t=_norm(str(u.get('text','')))
        words=t.split()
        stats[s]['turns'] += 1
        stats[s]['words'] += len(words)
        if len(words) <= 3 and t in CLIENT_SHORT:
            stats[s]['short'] += 1
            score[s] -= 2.2
        for phrase, weight in AGENT_PHRASES.items():
            if phrase in t: score[s] += weight
        is_q = ('?' in str(u.get('text',''))) or any(t.startswith(q) for q in QUESTION_WORDS)
        if is_q:
            stats[s]['questions'] += 1
            score[s] += 1.8
        if t.startswith('porque ') and len(words) >= 4:
            score[s] -= 0.7
    for s in speakers:
        st=stats[s]
        if st['turns']:
            score[s] += min(4.0, st['questions'] * 0.5)
            score[s] -= min(3.0, st['short'] * 0.6)
    agent=max(speakers, key=lambda s: score[s])
    client=speakers[1] if speakers[0] == agent else speakers[0]
    return {agent: agent_label, client: client_label}
