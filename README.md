# AUDITOR IA - TRANSCRIPTOR 7.0.0

Versión Windows enfocada exclusivamente en **transcripción de archivos con alta precisión e identificación AGENTE / CLIENTE**.

## Cambio principal

La versión 7.0.0 deja de usar Faster-Whisper + pyannote como motor principal. Los archivos se procesan con:

- `gpt-4o-transcribe-diarize`: transcripción + diarización integrada.
- `gpt-5.6-luna`: segunda revisión semántica para decidir qué speaker corresponde a AGENTE y cuál a CLIENTE.
- Muestra opcional de voz del agente de 2–10 segundos para fijar un hablante conocido cuando esté disponible.

Si la primera transcripción confirma solo un hablante, el programa hace un segundo intento con VAD más sensible. Si aun así no puede confirmar dos voces, **no inventa etiquetas**: informa que la separación no es segura.

## Interfaz 7.0

Solo existen tres secciones:

1. **Transcribir**: cargar audio, procesar, corregir etiquetas y exportar.
2. **Historial**: recuperar transcripciones anteriores.
3. **Ajustes**: API key, muestra opcional de voz y preferencias.

Se eliminaron Inicio, En Vivo, paneles técnicos y opciones que recargaban la interfaz.

## Distribución

Solo se genera:

`AUDITOR_IA_7.0.0_Setup.exe`

No se genera Portable.

## Requisitos de uso

- Windows 10/11 x64.
- Conexión a Internet.
- API key de OpenAI con acceso al modelo de transcripción.
- Facturación/API disponible en la cuenta correspondiente.

La API key se guarda cifrada con Windows DPAPI para el usuario actual. También se admite la variable de entorno `OPENAI_API_KEY`.

## GitHub

```bat
git add -A
git commit -m "AUDITOR IA 7.0.0 Alta Precision"
git push origin main
```

Después ejecutar manualmente **Build Windows Installer** en GitHub Actions.

Solo cuando el instalador haya sido probado con audios reales conviene crear el tag `v7.0.0`.
