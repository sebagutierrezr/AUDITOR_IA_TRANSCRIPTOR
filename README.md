# AUDITOR IA 6.1.0

Versión enfocada en la calidad de identificación Agente/Cliente.

## Motores incluidos

- Faster-Whisper Base: perfil Rápido.
- Faster-Whisper Small: perfil Balanceado.
- pyannote Community-1: identificación neuronal de voces.

Los tres modelos se incluyen en el instalador y en el portable. La aplicación
no descarga modelos durante el uso.

## Identificación

- Audio preparado como WAV mono de 16 kHz.
- Exactamente dos participantes.
- El primer participante se asigna según la configuración.
- Cruce de tiempos por mayor solapamiento.
- Corrección manual disponible en el panel.

## Requisito para construir en GitHub

Community-1 requiere aceptar sus condiciones y usar un token de Hugging Face.

1. Aceptar condiciones en:
   `pyannote/speaker-diarization-community-1`
2. Crear un token de lectura en Hugging Face.
3. En GitHub: Settings > Secrets and variables > Actions.
4. Crear el secreto `HF_TOKEN`.
5. Ejecutar el workflow o crear el tag `v6.1.0`.

El token solo se usa durante la compilación. No queda dentro del instalador.
