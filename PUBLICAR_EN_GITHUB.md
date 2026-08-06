# Publicar AUDITOR IA 6.0 en GitHub

Este proyecto genera automáticamente:

- `AUDITOR_IA_6.0_Setup.exe`
- `AUDITOR_IA_6.0_Portable.zip`

## Opción recomendada: GitHub Actions

1. Copia todo el contenido de esta carpeta a la raíz del repositorio.
2. Confirma que exista `.github/workflows/build-release.yml`.
3. Sube los cambios a GitHub.
4. Crea y publica el tag `v6.0.0`.

Comandos:

```bat
git add .
git commit -m "Preparar distribución Windows 6.0"
git push origin main
git tag v6.0.0
git push origin v6.0.0
```

GitHub ejecutará Windows, construirá ambos archivos y los publicará en **Releases**.

También se pueden generar sin crear un tag:

1. Abre la pestaña **Actions** del repositorio.
2. Selecciona **Build Windows release**.
3. Presiona **Run workflow**.
4. Descarga el artefacto `AUDITOR_IA_6.0_Windows`.

## Enlaces para compartir

Después de publicar el release:

- Página: `https://github.com/sebagutierrezr/AUDITOR_IA_TRANSCRIPTOR/releases/latest`
- Portable: `https://github.com/sebagutierrezr/AUDITOR_IA_TRANSCRIPTOR/releases/latest/download/AUDITOR_IA_6.0_Portable.zip`
- Instalador: `https://github.com/sebagutierrezr/AUDITOR_IA_TRANSCRIPTOR/releases/latest/download/AUDITOR_IA_6.0_Setup.exe`

## Importante

- El usuario final no necesita Python.
- El portable debe extraerse antes de ejecutarse.
- La primera carga de un modelo puede requerir internet.
- Los modelos descargados se guardan en la carpeta `models` junto a la aplicación.
