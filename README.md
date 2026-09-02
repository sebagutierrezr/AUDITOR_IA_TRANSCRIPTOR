# AUDITOR IA - TRANSCRIPTOR 8.0.0

Motor de archivos reconstruido con **NVIDIA NeMo-Speech.cpp + Nemotron 3.5 ASR + SortFormer v2**.

- Español forzado (`es-ES`).
- Diarización integrada a nivel palabra.
- Reconstrucción de turnos por `speaker_tag` de cada palabra.
- Clasificación contextual posterior a AGENTE / CLIENTE.
- Sin API ni pagos por uso.
- Modelos incluidos en el Setup.
- En Vivo se conserva sobre el motor estable previo mientras se valida migración nativa de captura.

El workflow de GitHub compila el runtime CPU oficial de NVIDIA, convierte los modelos públicos a GGUF Q8 y genera `AUDITOR_IA_8.0.0_Setup.exe`.
