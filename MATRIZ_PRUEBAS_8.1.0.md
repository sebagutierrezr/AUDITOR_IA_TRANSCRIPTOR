# Matriz de aceptación 8.1.0 UNIVERSAL

Una build no debe considerarse estable solo porque compila. Antes de liberar al usuario final deben verificarse en Windows real:

| Área | Prueba | Resultado esperado |
|---|---|---|
| Instalación | PC Windows 10 x64 limpio | Instala y abre sin Python/Git/CUDA |
| Instalación | PC Windows 11 x64 limpio | Instala y abre sin dependencias manuales |
| Upgrade | Instalar sobre 8.0.x | Conserva datos de usuario y actualiza binarios |
| CPU | PC sin NVIDIA | Transcribe archivos y En vivo |
| Bajo recurso | 6-8 GB RAM | AUTO elige ECO/Base y no congela UI |
| Audio | Micrófono integrado | AGENTE recibe señal |
| Audio | Headset USB | AGENTE y CLIENTE se seleccionan dinámicamente |
| Audio | Bluetooth compatible | Enumera dispositivos y muestra error claro si loopback no está disponible |
| Loopback | YouTube/audio PC | Solo CLIENTE recibe el audio del PC |
| Eco | Audio PC se filtra al micrófono | No duplica la misma frase como AGENTE |
| En vivo | Silencio 60 s | No inventa frases |
| En vivo | Iniciar/detener 10 veces | Todas las sesiones vuelven a abrir audio |
| En vivo | Segunda sesión | Funciona igual que la primera |
| UI | Scroll hacia arriba mientras transcribe | Vista permanece donde el usuario la dejó |
| UI | Reactivar AUTO-SEGUIR | Salta al último texto y continúa |
| Dispositivo | Desconectar/reconectar headset | Actualizar dispositivos permite recuperarlo |
| Archivo | MP3/WAV/M4A largos | UI permanece responsiva |
| Exportación | TXT y DOCX | Genera archivos válidos |
| Cierre | Cerrar app durante En vivo | Streams/hilos se cierran sin proceso huérfano |
| Diagnóstico | Falta loopback/modelo | Indica componente exacto y no simula LISTO |
