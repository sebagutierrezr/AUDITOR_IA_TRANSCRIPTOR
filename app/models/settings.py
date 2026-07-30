from dataclasses import dataclass, asdict

@dataclass
class AppSettings:
    language: str = "ES"
    transcription_engine: str = "WHISPER.CPP"
    file_profile: str = "BALANCEADO"
    live_profile: str = "RAPIDO"
    uppercase: bool = True
    first_speaker_agent: bool = False
    show_timestamps: bool = True
    def to_dict(self): return asdict(self)
    @classmethod
    def from_dict(cls, data):
        d = cls()
        return cls(
            language=data.get("language", d.language),
            transcription_engine=data.get("transcription_engine", d.transcription_engine),
            file_profile=data.get("file_profile", d.file_profile),
            live_profile=data.get("live_profile", d.live_profile),
            uppercase=bool(data.get("uppercase", d.uppercase)),
            first_speaker_agent=bool(data.get("first_speaker_agent", d.first_speaker_agent)),
            show_timestamps=bool(data.get("show_timestamps", d.show_timestamps)),
        )
