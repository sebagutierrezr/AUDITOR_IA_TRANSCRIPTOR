# V6.1.0 — Identificación profesional Agente/Cliente

- Sustituida la diarización simplificada por pyannote Community-1.
- El motor trabaja con exactamente dos participantes.
- Se usa la diarización exclusiva para reconciliar tiempos con Whisper.
- Cada intervención se asigna por mayor solapamiento temporal.
- No se alternan etiquetas de manera artificial.
- Los fallos de identificación ya no generan resultados etiquetados inseguros.
- Modelos Base, Small y Community-1 incluidos en Setup y Portable.
- Verificación previa de transcripción e identificación.
- PyTorch CPU para compatibilidad con equipos sin tarjeta gráfica.
- Release objetivo: v6.1.0.

# V6.0.1 — Modelos incluidos y verificados

- Modelos Base y Small incluidos en Setup y Portable.
- No se descargan modelos al comenzar una transcripción.
- Verificación visible en Configuración.
- La transcripción se bloquea con un mensaje claro si un modelo está incompleto.
- Faster-Whisper usa rutas locales y `local_files_only=True`.
- Eliminado el estado falso `is_ready=True`.
- Release preparado como `v6.0.1`.

# V6.0 — Consolidada

- Un único motor: Faster-Whisper.
- Perfiles Base, Small y Medium.
- Recomendación según memoria del equipo.
- Transcripción de archivos mono.
- Etiquetas automáticas Agente/Cliente.
- Diarización NumPy sin scikit-learn.
- Corrección manual de hablantes.
- Exportación TXT y Word en segundo plano.
- Guardado automático y botón Abrir carpeta.
- Selector interno estable.
- En vivo conservado sin cambios funcionales.

# V4.7.5.2 — Etiquetas Agente y Cliente restauradas

- Restaurada la identificación automática de hablantes para archivos mono.
- Las intervenciones vuelven a etiquetarse como AGENTE y CLIENTE.
- Se respetan los nombres definidos en Configuración.
- Si la identificación automática falla, la transcripción no se pierde.
- Los botones Marcar como Agente y Marcar como Cliente permanecen disponibles.
- Se conserva el selector estable y la transcripción mono funcional.
- Módulo En vivo sin modificaciones.

# V4.7.5.1 — Selector estable

- Retirado el selector nativo de Windows que provocaba "No responde".
- Selector interno Qt en modo Detalles y tamaño amplio.
- Se conservan Marcar como Agente y Marcar como Cliente.
- Se conserva la barra de acciones sobre el editor.
- Se conserva intacta la transcripción mono funcional.
- Módulo En vivo sin modificaciones.

# V4.7.5 — Selector, hablantes y barra superior

- Restaurado el selector normal de archivos de Windows.
- Restaurados los botones Marcar como Agente y Marcar como Cliente.
- El cambio de hablante funciona sobre la línea actual o una selección.
- Los botones de exportación se movieron sobre el editor.
- Ningún botón queda superpuesto sobre la transcripción.
- El editor usa altura flexible y conserva su barra de desplazamiento.
- Se mantienen intactas la carga y transcripción mono de V4.7.4.
- Módulo En vivo sin modificaciones.

# V4.7.4 — Archivos mono

- Módulo Archivos reconstruido desde la base estable V4.7.2.
- Panel visual alineado con el módulo En vivo.
- Selector de archivos no nativo para evitar congelamientos de Windows.
- La interfaz no abre ni analiza audio al seleccionar.
- Conversión completa en QThread mediante PyAV.
- Todo archivo se transforma a WAV mono de 16 kHz.
- Eliminada la dependencia imageio-ffmpeg.
- Eliminada la diarización automática del flujo principal para priorizar estabilidad.
- Transcripción editable y exportable a TXT y Word.
- Módulo En vivo conservado sin cambios.

# V4.7.2 — Ajustes en vivo

- La conversación se desplaza automáticamente hasta la intervención más reciente.
- La sensibilidad de agente y cliente puede modificarse durante la sesión.
- Nuevo regulador global de filtro de ruido, ajustable durante la sesión.
- Los cambios actualizan directamente el VAD activo sin reiniciar dispositivos.
- Se conserva la captura y la transcripción funcional de V4.7.1.
- El modo Ampliar transcripción se mantiene.

# V4.7.1 — Base exacta corregida

- Construida directamente desde el ZIP V4.7 entregado por el usuario.
- El micrófono conserva el índice predeterminado exacto de Windows.
- Ya no se reemplaza silenciosamente MME por WASAPI del mismo headset.
- Captura, VAD, sensibilidad y transcripción del cliente se conservan.
- Panel de configuración V4.7 sin cambios.
- Área de transcripción ampliable.
- Intervenciones diferenciadas visualmente por hablante.

# V4.7 — Sensibilidad ajustable

- Regulador independiente para entrada y salida.
- Entrada predeterminada en 75 %.
- Salida predeterminada en 70 %.
- Los valores modifican directamente los umbrales del VAD.
- Faster-Whisper no aplica un segundo filtro VAD.
- Se conserva la captura y el panel de configuración de V4.6.

# V4.6 — Transcripción corregida

- Panel de configuración restaurado exactamente desde V4.3.2.
- Captura, VAD y dispositivos sin modificaciones.
- transcribe_live validado dentro de FasterWhisperEngine.
- Eliminado initial_prompt para evitar texto inventado desde instrucciones.
- Filtro posterior para AMARA, subtítulos y frases conocidas.
- Área de transcripción ampliada a 500 px mínimos.
- Editor con mayor tamaño de fuente, padding y contraste.
- Acciones de etiquetado y exportación simplificadas.

# V4.3.2 — Transcripción restaurada

- transcribe_live volvió a quedar dentro de FasterWhisperEngine.
- release y _format_time también quedaron restaurados dentro de la clase.
- Eliminados parámetros no esenciales para asegurar compatibilidad con
  faster-whisper 1.2.x.
- Se conserva la detección de ambas fuentes y la configuración de fidelidad.

# V4.3.1 — Inicio corregido

- Corregidos cinco métodos que habían quedado fuera de UnifiedAudioWorker.
- Restauradas normalización, remuestreo y escritura WAV.
- Corregido el cierre inmediato al procesar la primera frase.
- Agregada validación de estabilidad después de abrir ambas fuentes.
- Los fallos de audio ya no se presentan como una finalización normal.
- Se conserva la fidelidad y el panel profesional de V4.3.

# V4.3 — Fidelidad mejorada

- Perfil en vivo cambiado de Base/Rápido a Faster-Whisper Small.
- Idioma español fijado para entrevistas.
- Beam search aumentado a 5.
- Segmentos de voz entre 0,85 y 12 segundos.
- Pausa de cierre aumentada para evitar frases cortadas.
- Normalización por RMS limitada a 7x.
- Eliminada la amplificación extrema de ruido.
- Rechazo de fragmentos sin señal útil.
- Filtro de repeticiones y frases típicas de alucinación.
- Panel profesional recuperado desde V4.1.
- Entrada y salida mantienen la captura funcional de V4.2.
