# AUDITOR IA - TRANSCRIPTOR 8.0.1 STABLE

Aplicación de escritorio Windows para transcribir entrevistas telefónicas de forma local, sin API y sin pagos por uso.

## Arquitectura 8.0.1

### Archivos
- **Faster-Whisper Small (CTranslate2, CPU int8)** para transcripción y timestamps por palabra.
- **NVIDIA SortFormer v2 / NeMo-Speech.cpp** exclusivamente para separación acústica de hablantes.
- Clasificador contextual posterior para traducir los clusters acústicos a **AGENTE / CLIENTE**.
- Si SortFormer falla o supera su tiempo máximo, la transcripción no se pierde: se entrega el texto con un respaldo contextual de roles.
- El procesamiento pesado se ejecuta en un proceso separado y la interfaz permanece independiente.
- La comunicación GUI/worker se hace mediante JSON en LOCALAPPDATA; no depende de stdout de un EXE PyInstaller sin consola.
- El worker tiene prioridad reducida y un watchdog evita esperas indefinidas.

### En vivo
- Micrófono del agente: `sounddevice`.
- Audio del cliente: **WASAPI loopback** mediante `PyAudioWPatch`.
- Captura y transcripción se ejecutan en hilos distintos.
- Faster-Whisper se precarga sin bloquear la interfaz y usa decodificación de baja latencia para fragmentos en vivo.
- Las grabaciones se guardan en `%LOCALAPPDATA%\\AUDITOR_IA_TRANSCRIPTOR\\recordings`, no en Program Files.

## Build

El workflow `Build Windows Installer 8.0.1 STABLE`:
1. instala dependencias Python de la app;
2. incorpora FFmpeg Shared portable;
3. descarga el binario oficial CPU de NeMo-Speech.cpp v0.1.0 para Windows x64;
4. convierte SortFormer v2 Q8 en un entorno Python aislado;
5. descarga Faster-Whisper Small;
6. ejecuta tests y validación del runtime empaquetado;
7. prueba explícitamente el modo `--file-worker` del EXE;
8. genera `AUDITOR_IA_8.0.1_Setup.exe`.

El instalador conserva el mismo AppId de 8.0.0 para actualizar la instalación existente.
