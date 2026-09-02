from __future__ import annotations
import json, os, re, subprocess, sys
from pathlib import Path
from app.services.paths_service import AppPaths
from app.services.role_classifier import infer_role_map

class NemoSpeechService:
    def __init__(self):
        self.paths=AppPaths()

    @property
    def runtime(self) -> Path:
        root = Path(getattr(sys, '_MEIPASS', self.paths.root))
        candidates=[
            root/'nemo-speech'/'bin'/'nemo-speech.exe',
            self.paths.root/'nemo-speech'/'bin'/'nemo-speech.exe',
            root/'runtime'/'nemo-speech.exe',
        ]
        for p in candidates:
            if p.is_file(): return p
        return candidates[0]

    @property
    def asr_model(self) -> Path:
        root=Path(getattr(sys,'_MEIPASS',self.paths.root))
        for p in [root/'models'/'nemotron-3.5-asr-streaming-0.6b.q8_0.gguf', self.paths.models/'nemotron-3.5-asr-streaming-0.6b.q8_0.gguf']:
            if p.is_file(): return p
        return root/'models'/'nemotron-3.5-asr-streaming-0.6b.q8_0.gguf'

    @property
    def diar_model(self) -> Path:
        root=Path(getattr(sys,'_MEIPASS',self.paths.root))
        for p in [root/'models'/'sortformer-v2-q8_0.gguf', self.paths.models/'sortformer-v2-q8_0.gguf']:
            if p.is_file(): return p
        return root/'models'/'sortformer-v2-q8_0.gguf'

    def is_ready(self):
        return self.runtime.is_file() and self.asr_model.is_file() and self.diar_model.is_file()

    @staticmethod
    def _collect_words(obj):
        found=[]
        def walk(x):
            if isinstance(x,dict):
                if ('word' in x or 'text' in x) and any(k in x for k in ('speaker_tag','speaker','speaker_id')) and any(k in x for k in ('start_time','start','start_sec')):
                    found.append(x)
                for v in x.values(): walk(v)
            elif isinstance(x,list):
                for v in x: walk(v)
        walk(obj)
        return found

    @staticmethod
    def _seconds(v):
        try: x=float(v)
        except: return 0.0
        # Riva-shaped JSON commonly uses ms; CLI may use seconds.
        return x/1000.0 if x > 1000 else x

    def transcribe(self, wav: Path, agent_label='AGENTE', client_label='CLIENTE', uppercase=True, progress=None):
        if not self.is_ready():
            raise RuntimeError('MOTOR NEMO/SORTFORMER NO ESTA INSTALADO O ESTA INCOMPLETO.')
        cmd=[str(self.runtime),'transcribe',str(wav),'--model',str(self.asr_model),'--diar-model',str(self.diar_model),'--diar-preset','offline','--json','--word-times','--device','cpu','--language','es-ES']
        if progress: progress(30,'NEMOTRON 3.5 + SORTFORMER: TRANSCRIBIENDO Y SEPARANDO VOCES...')
        flags=0
        if os.name=='nt': flags=getattr(subprocess,'CREATE_NO_WINDOW',0)
        proc=subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace', creationflags=flags)
        if proc.returncode != 0:
            raise RuntimeError('NEMO-SPEECH FALLO: '+(proc.stderr[-1200:] or proc.stdout[-1200:]))
        raw=proc.stdout.strip()
        try: data=json.loads(raw)
        except json.JSONDecodeError:
            # Some builds may prepend a short status line; recover the JSON envelope.
            a=min([i for i in (raw.find('{'),raw.find('[')) if i>=0], default=-1)
            if a<0: raise RuntimeError('NEMO-SPEECH NO DEVOLVIO JSON ESTRUCTURADO.')
            data=json.loads(raw[a:])
        words=self._collect_words(data)
        if not words:
            raise RuntimeError('NEMO-SPEECH NO DEVOLVIO PALABRAS CON SPEAKER TAG.')
        norm=[]
        for w in words:
            text=str(w.get('word',w.get('text',''))).strip()
            if not text: continue
            sp=str(w.get('speaker_tag',w.get('speaker',w.get('speaker_id','0'))))
            st=self._seconds(w.get('start_time',w.get('start',w.get('start_sec',0))))
            en=self._seconds(w.get('end_time',w.get('end',w.get('end_sec',st))))
            norm.append({'text':text,'speaker':sp,'start':st,'end':max(st,en)})
        norm.sort(key=lambda x:(x['start'],x['end']))
        # Rebuild turns directly from word-level speaker tags. Never assign an entire ASR sentence to one speaker.
        turns=[]
        for w in norm:
            if turns and turns[-1]['speaker']==w['speaker'] and w['start']-turns[-1]['end'] <= 0.9:
                turns[-1]['words'].append(w); turns[-1]['end']=max(turns[-1]['end'],w['end'])
            else:
                turns.append({'speaker':w['speaker'],'start':w['start'],'end':w['end'],'words':[w]})
        for t in turns:
            t['text']=' '.join(w['text'] for w in t['words']).strip()
        if progress: progress(92,'DETERMINANDO AGENTE Y CLIENTE POR CONTEXTO...')
        role_map=infer_role_map(turns,agent_label,client_label)
        out=[]
        for t in turns:
            label=role_map.get(t['speaker'], f'HABLANTE {t["speaker"]}')
            body=t['text'].upper() if uppercase else t['text']
            out.append({'start':t['start'],'end':t['end'],'speaker':label,'text':f'[{t["start"]:07.2f}] {label}: {body}','words':t['words']})
        return out
