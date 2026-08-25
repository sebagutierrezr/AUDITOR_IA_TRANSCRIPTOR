from dataclasses import dataclass, field


@dataclass
class Segment:
    start: float
    end: float
    text: str
    speaker: str = "HABLANTE"
    confidence: float | None = None

    # Metadatos internos para alinear palabras con cambios de hablante.
    # La UI y las exportaciones siguen utilizando Segment.text normalmente.
    words: list[dict] = field(default_factory=list)


@dataclass
class Conversation:
    source_path: str
    language: str
    segments: list[Segment] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(segment.text for segment in self.segments).strip()
