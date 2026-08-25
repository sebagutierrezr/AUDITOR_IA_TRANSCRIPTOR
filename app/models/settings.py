from dataclasses import asdict, dataclass


@dataclass
class AppSettings:
    language: str = "ES"
    transcription_engine: str = "FASTER-WHISPER"
    file_profile: str = "ALTA"
    live_profile: str = "ALTA"
    uppercase: bool = True
    first_speaker_agent: bool = False
    show_timestamps: bool = True
    speaker_one_label: str = "AGENTE"
    speaker_two_label: str = "CLIENTE"
    diarization_enabled: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AppSettings":
        defaults = cls()
        return cls(
            language=str(data.get("language", defaults.language)),
            transcription_engine="FASTER-WHISPER",
            file_profile="ALTA",
            live_profile="ALTA",
            uppercase=bool(data.get("uppercase", defaults.uppercase)),
            first_speaker_agent=bool(
                data.get("first_speaker_agent", defaults.first_speaker_agent)
            ),
            show_timestamps=bool(
                data.get("show_timestamps", defaults.show_timestamps)
            ),
            speaker_one_label=str(
                data.get("speaker_one_label", defaults.speaker_one_label)
            ).strip() or defaults.speaker_one_label,
            speaker_two_label=str(
                data.get("speaker_two_label", defaults.speaker_two_label)
            ).strip() or defaults.speaker_two_label,
            diarization_enabled=True,
        )
