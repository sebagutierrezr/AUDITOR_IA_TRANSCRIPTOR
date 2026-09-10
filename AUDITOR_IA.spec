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

# PyAudioWPatch contiene una extensión nativa; sounddevice incluye runtime de
# PortAudio/cffi según la rueda. Collect_all evita que el EXE funcione en CI pero
# pierda el backend de audio al instalarlo en otro PC.
for package in ('pyaudiowpatch', 'sounddevice'):
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
        'soundcard',
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
    name='AUDITOR_IA_8.0.1_BUILD',
)
