from __future__ import annotations
import json, logging, os, sys, time
from pathlib import Path
EVENT_PREFIX='AUDITOR_EVENT|'
def emit_event(kind,**payload): print(EVENT_PREFIX+json.dumps({'type':kind,**payload},ensure_ascii=False,separators=(',',':')),flush=True)
class Progress:
    def __init__(self): self.v=-1; self.t=0
    def __call__(self,v,m):
        now=time.monotonic(); v=int(max(0,min(100,v)))
        if v!=self.v or now-self.t>.5:
            self.v=v; self.t=now; emit_event('progress',value=v,message=m)
def run_job(job_path:Path):
    from app.services.audio_conversion_service import AudioConversionService
    from app.services.paths_service import AppPaths
    from app.services.nemo_speech_service import NemoSpeechService
    p=Progress(); prepared=None
    try:
        job=json.loads(job_path.read_text(encoding='utf-8'))
        audio=Path(job['audio_path']); result=Path(job['result_path'])
        emit_event('started',message='PROCESO INICIADO')
        p(2,'PREPARANDO AUDIO...')
        prepared=AudioConversionService(AppPaths()).convert_to_mono_wav(audio,p)
        service=NemoSpeechService()
        segments=service.transcribe(prepared,job.get('speaker_one_label','AGENTE'),job.get('speaker_two_label','CLIENTE'),bool(job.get('uppercase',True)),p)
        payload={'source_path':str(audio),'language':'ES','segments':segments}
        result.parent.mkdir(parents=True,exist_ok=True)
        result.write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8')
        p(100,'TRANSCRIPCION FINALIZADA'); emit_event('completed',result_path=str(result)); return 0
    except Exception as exc:
        emit_event('failed',error_type=type(exc).__name__,message=str(exc) or type(exc).__name__); return 2
    finally:
        if prepared:
            try: prepared.unlink(missing_ok=True)
            except: pass
def main(argv=None):
    argv=list(sys.argv[1:] if argv is None else argv)
    return run_job(Path(argv[0]).resolve()) if len(argv)==1 else 2
if __name__=='__main__': raise SystemExit(main())
