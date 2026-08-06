from dataclasses import asdict, dataclass


@dataclass
class AppSettings:
    language: str = "ES"
    transcription_engine: str = "FASTER-WHISPER"
    file_profile: str = "BALANCEADO"
    live_profile: str = "BALANCEADO"
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
            language=data.get("language", defaults.language),
            transcription_engine=data.get(
                "transcription_engine",
                defaults.transcription_engine,
            ),
            file_profile=data.get("file_profile", defaults.file_profile),
            live_profile=data.get("live_profile", defaults.live_profile),
            uppercase=bool(data.get("uppercase", defaults.uppercase)),
            first_speaker_agent=bool(
                data.get(
                    "first_speaker_agent",
                    defaults.first_speaker_agent,
                )
            ),
            show_timestamps=bool(
                data.get("show_timestamps", defaults.show_timestamps)
            ),
            speaker_one_label=str(
                data.get(
                    "speaker_one_label",
                    defaults.speaker_one_label,
                )
            ).strip() or defaults.speaker_one_label,
            speaker_two_label=str(
                data.get(
                    "speaker_two_label",
                    defaults.speaker_two_label,
                )
            ).strip() or defaults.speaker_two_label,
            diarization_enabled=bool(
                data.get(
                    "diarization_enabled",
                    defaults.diarization_enabled,
                )
            ),
        )
