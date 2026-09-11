# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_data_files

root = Path.cwd()

datas = [
    ('resources', 'resources'),
    ('config', 'config'),
]

for source, target in [
    ('build_assets/models/small', 'models/small'),
    ('build_assets/models/base', 'models/base'),
    ('build_assets/models/sortformer-v2-q8_0.gguf', 'models'),
    ('build_assets/nemo-speech', 'nemo-speech'),
    ('build_assets/ffmpeg', 'ffmpeg'),
]:
    path = root / source
    if not path.exists():
        raise RuntimeError(f'Falta activo de build requerido por PyInstaller: {path}')
    datas.append((str(path), target))

datas += collect_data_files('faster_whisper')

binaries = []
hiddenimports = [
    'docx',
    'faster_whisper',
    'ctranslate2',
    'av',
    'psutil',
]

# Audio universal: PyAudioWPatch es el backend WASAPI principal; SoundCard
# queda como fallback y sounddevice maneja el micrófono.
for package in ('pyaudiowpatch', 'soundcard', 'sounddevice'):
    p_datas, p_binaries, p_hidden = collect_all(package)
    datas += p_datas
    binaries += p_binaries
    hiddenimports += p_hidden


a = Analysis(
    ['main.py'],
    pathex=[str(root)],
    binaries=binaries,
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
    contents_directory='.',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='AUDITOR_IA_8.1.0_BUILD',
)
