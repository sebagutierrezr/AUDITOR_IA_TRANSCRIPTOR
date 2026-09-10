# Changelog

## 8.0.1 STABLE
- Reparado el bloqueo de transcripción de archivos causado por IPC basado en stdout y procesos nativos con pipes sin drenar.
- Worker de archivos aislado con progreso/resultados JSON en LOCALAPPDATA.
- Watchdog de proceso para evitar esperas indefinidas.
- Faster-Whisper Small pasa a ser el ASR estable de archivos y En vivo.
- SortFormer queda desacoplado del ASR: un fallo de diarización ya no elimina la transcripción.
- SortFormer usa full-attention solo en audios cortos y modo streaming en llamadas largas.
- Añadido timeout y prioridad reducida al proceso nativo de diarización.
- Mejorada la clasificación AGENTE / CLIENTE con corrección contextual posterior a la separación acústica.
- Reparado En vivo: las grabaciones ya no intentan escribirse dentro de Program Files.
- Captura del cliente migrada a WASAPI loopback con PyAudioWPatch.
- Captura y transcripción En vivo separadas en hilos independientes para evitar congelamientos.
- Decodificación En vivo optimizada a baja latencia.
- Workflow usa binario oficial NeMo-Speech.cpp v0.1.0 y aísla las dependencias del conversor para no alterar el entorno de la app.
- PyInstaller incluye explícitamente runtime nativo de PyAudioWPatch/sounddevice.
- Build valida el EXE empaquetado y el modo `--file-worker` antes de crear el Setup.

## 8.0.0
- Primera integración experimental de NeMo-Speech.cpp/SortFormer.
