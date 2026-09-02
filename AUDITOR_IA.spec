# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
root=Path.cwd()
datas=[('resources','resources'),('config','config')]
for folder,target in [('build_assets/models','models'),('build_assets/nemo-speech','nemo-speech'),('build_assets/ffmpeg','ffmpeg')]:
    p=root/folder
    if p.exists(): datas.append((str(p),target))
hiddenimports=['soundcard','sounddevice','docx','faster_whisper','ctranslate2','av']
a=Analysis(['main.py'],pathex=[str(root)],binaries=[],datas=datas,hiddenimports=hiddenimports,hookspath=[],hooksconfig={},runtime_hooks=[],excludes=['torch','torchaudio','pyannote','speechbrain','sklearn'],noarchive=False)
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='AUDITOR_IA',debug=False,bootloader_ignore_signals=False,strip=False,upx=False,console=False,icon='resources/logo.ico')
coll=COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,upx_exclude=[],name='AUDITOR_IA_8.0.0_BUILD')
