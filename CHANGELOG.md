# CHANGELOG

## 8.1.0 UNIVERSAL

### Arquitectura
- Versión centralizada en `app/version.py`.
- Perfil automático de hardware por CPU/RAM.
- Faster-Whisper Base para ECO y Small para BALANCEADO/CALIDAD.
- CPU como runtime base; no exige GPU.
- Logging rotativo con límite de tamaño.

### Audio
- PyAudioWPatch/WASAPI como loopback principal.
- SoundCard como fallback automático.
- Micrófono mediante sounddevice.
- Dispositivos persistidos por identificador lógico, no por marca fija.
- Calibración de ruido al iniciar sesión.
- Captura loopback por callback para que STOP no quede esperando audio del PC.
- Cola de trabajos acotada para equipos lentos.
- Cierre explícito de streams e hilos al detener y cerrar la aplicación.

### Calidad En vivo
- Firma acústica temporal/espectral para detectar eco del audio del PC en el micrófono.
- Conserva CLIENTE como fuente autoritativa cuando existe duplicación.
- Refuerzo de filtros contra CTAs/alucinaciones y repeticiones patológicas.
- VAD y decodificación adaptados al perfil de hardware.

### Interfaz
- Scroll manual independiente mientras sigue llegando texto.
- AUTO-SEGUIR persistente y opcional.
- Ajustes de rendimiento y backend de audio.
- Diagnóstico del equipo desde la aplicación.

### Distribución
- Modelos Base y Small incluidos.
- PyAudioWPatch incluido en el instalador.
- Workflow, PyInstaller, Inno Setup y Setup actualizados a 8.1.0.
- Conserva AppId de 8.0 para actualizar instalaciones existentes.
