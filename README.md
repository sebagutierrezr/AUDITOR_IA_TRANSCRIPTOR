# AUDITOR IA - TRANSCRIPTOR 8.1.0 UNIVERSAL

Aplicación de escritorio Windows para transcripción local de entrevistas, separación de hablantes y transcripción En vivo sin API ni servicios de pago.

## Objetivo de 8.1.0

8.1.0 deja de asumir un headset o un computador específico. La aplicación detecta el hardware y los dispositivos de audio en cada equipo y selecciona una configuración segura automáticamente.

### Compatibilidad objetivo

- Windows 10/11 de 64 bits.
- CPU x64 como requisito base; NVIDIA/CUDA no es obligatorio.
- 6 GB RAM mínimo funcional; 8 GB o más recomendado.
- Micrófonos USB, jack, integrados y dispositivos de audio compatibles con Windows.
- Audio del cliente mediante WASAPI loopback.
- PyAudioWPatch como backend de loopback principal y SoundCard como fallback.

## En vivo

- AGENTE: siempre proviene del micrófono seleccionado.
- CLIENTE: siempre proviene del loopback de la salida de Windows seleccionada.
- El backend y el dispositivo se resuelven dinámicamente; no hay nombres de hardware codificados.
- Calibración inicial del ruido ambiente.
- VAD adaptativo, filtro de silencio y control de alucinaciones.
- Firma acústica no biométrica para detectar cuando el audio del PC se filtra por el micrófono y evitar duplicarlo como AGENTE.
- Cola de audio acotada para evitar consumo ilimitado de memoria en PCs lentos.
- STOP y reinicio de sesión cierran streams e hilos de captura.
- Scroll manual durante la transcripción y auto-seguimiento opcional.

## Adaptación al equipo

Modo AUTO elige un perfil según CPU y RAM:

- ECO: Faster-Whisper Base, pocos threads y baja latencia. Pensado para equipos limitados.
- BALANCEADO: Faster-Whisper Small con carga moderada.
- CALIDAD: Faster-Whisper Small con mayor búsqueda de decodificación.

El usuario puede forzar ECO, BALANCEADO o CALIDAD en Ajustes.

## Diagnóstico

Ajustes incluye diagnóstico de:

- Windows/arquitectura.
- CPU y RAM.
- carpetas de usuario con permisos de escritura.
- Faster-Whisper.
- SortFormer/NeMo-Speech.
- FFmpeg.
- micrófonos detectados.
- salidas de Windows y backend loopback disponible.

Los logs rotativos se guardan en `%LOCALAPPDATA%\AUDITOR_IA_TRANSCRIPTOR\logs`.

## Datos de usuario

La instalación es de solo lectura. Todo dato modificable se guarda bajo `%LOCALAPPDATA%\AUDITOR_IA_TRANSCRIPTOR`:

- `config`: preferencias.
- `recordings`: grabaciones En vivo.
- `exports`: exportaciones.
- `history/data`: historial.
- `logs`: diagnóstico.
- `temp`: temporales.

## Build

GitHub Actions construye un único instalador x64 e incluye:

- Python runtime empaquetado con PyInstaller.
- Faster-Whisper Base + Small.
- FFmpeg Shared.
- NeMo-Speech CPU + SortFormer.
- PyAudioWPatch, SoundCard y sounddevice.

El build ejecuta compileall, unit tests y una autoprueba del EXE empaquetado antes de crear el instalador.

Salida:

`AUDITOR_IA_8.1.0_Setup.exe`
