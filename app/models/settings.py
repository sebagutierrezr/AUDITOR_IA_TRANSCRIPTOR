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

    # 8.1 Universal
    performance_mode: str = "AUTO"  # AUTO / ECO / BALANCEADO / CALIDAD
    audio_backend: str = "AUTO"     # AUTO / PYAUDIOWPATCH / SOUNDCARD
    live_auto_follow: bool = True
    live_agent_sensitivity: int = 58
    live_client_sensitivity: int = 64
    live_noise_filter: int = 45
    preferred_input_uid: str = ""
    preferred_output_uid: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def _percent(value, default: int) -> int:
        try:
            return max(0, min(100, int(value)))
        except Exception:
            return default

    @classmethod
    def from_dict(cls, data: dict) -> "AppSettings":
        defaults = cls()
        performance = str(data.get("performance_mode", defaults.performance_mode)).upper()
        if performance not in {"AUTO", "ECO", "BALANCEADO", "CALIDAD"}:
            performance = "AUTO"
        backend = str(data.get("audio_backend", defaults.audio_backend)).upper()
        if backend not in {"AUTO", "PYAUDIOWPATCH", "SOUNDCARD"}:
            backend = "AUTO"
        return cls(
            language=str(data.get("language", defaults.language)),
            transcription_engine="FASTER-WHISPER",
            file_profile="ALTA",
            live_profile="ALTA",
            uppercase=bool(data.get("uppercase", defaults.uppercase)),
            first_speaker_agent=bool(data.get("first_speaker_agent", defaults.first_speaker_agent)),
            show_timestamps=bool(data.get("show_timestamps", defaults.show_timestamps)),
            speaker_one_label=str(data.get("speaker_one_label", defaults.speaker_one_label)).strip() or defaults.speaker_one_label,
            speaker_two_label=str(data.get("speaker_two_label", defaults.speaker_two_label)).strip() or defaults.speaker_two_label,
            diarization_enabled=True,
            performance_mode=performance,
            audio_backend=backend,
            live_auto_follow=bool(data.get("live_auto_follow", defaults.live_auto_follow)),
            live_agent_sensitivity=cls._percent(data.get("live_agent_sensitivity"), defaults.live_agent_sensitivity),
            live_client_sensitivity=cls._percent(data.get("live_client_sensitivity"), defaults.live_client_sensitivity),
            live_noise_filter=cls._percent(data.get("live_noise_filter"), defaults.live_noise_filter),
            preferred_input_uid=str(data.get("preferred_input_uid", "") or ""),
            preferred_output_uid=str(data.get("preferred_output_uid", "") or ""),
        )
