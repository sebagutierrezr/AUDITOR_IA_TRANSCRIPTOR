from dataclasses import asdict, dataclass


@dataclass
class AppSettings:
    language: str = "ES"
    uppercase: bool = True
    show_timestamps: bool = True
    speaker_one_label: str = "AGENTE"
    speaker_two_label: str = "CLIENTE"
    agent_reference_path: str = ""
    role_model: str = "gpt-5.6-luna"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AppSettings":
        defaults = cls()
        return cls(
            language=str(data.get("language", defaults.language)).upper(),
            uppercase=bool(data.get("uppercase", defaults.uppercase)),
            show_timestamps=bool(data.get("show_timestamps", defaults.show_timestamps)),
            speaker_one_label=str(
                data.get("speaker_one_label", defaults.speaker_one_label)
            ).strip()
            or defaults.speaker_one_label,
            speaker_two_label=str(
                data.get("speaker_two_label", defaults.speaker_two_label)
            ).strip()
            or defaults.speaker_two_label,
            agent_reference_path=str(
                data.get("agent_reference_path", defaults.agent_reference_path)
            ).strip(),
            role_model=str(data.get("role_model", defaults.role_model)).strip()
            or defaults.role_model,
        )
