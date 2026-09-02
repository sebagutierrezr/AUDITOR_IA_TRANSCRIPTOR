# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

root = Path.cwd()

datas = [
    ('resources', 'resources'),
    ('config', 'config'),
]

for folder, target in [
    ('build_assets/models', 'models'),
    ('build_assets/nemo-speech', 'nemo-speech'),
    ('build_assets/ffmpeg', 'ffmpeg'),
]:
    path = root / folder
    if not path.exists():
        raise RuntimeError(f'Falta activo de build requerido por PyInstaller: {path}')
    datas.append((str(path), target))

hiddenimports = [
    'soundcard',
    'sounddevice',
    'docx',
    'faster_whisper',
    'ctranslate2',
    'av',
]

a = Analysis(
    ['main.py'],
    pathex=[str(root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'torch',
        'torchaudio',
        'torchcodec',
        'pyannote',
        'speechbrain',
        'sklearn',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AUDITOR_IA',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon='resources/logo.ico',
    # PyInstaller 6 pone los datos en _internal por defecto. La aplicacion
    # historicamente espera resources/, models/, ffmpeg/ y nemo-speech/ junto
    # al EXE. Forzamos el layout plano y eliminamos esa ambiguedad.
    contents_directory='.',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='AUDITOR_IA_8.0.0_BUILD',
)
