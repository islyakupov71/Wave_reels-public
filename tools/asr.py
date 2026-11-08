from faster_whisper import WhisperModel
import json, sys
A=sys.argv[1]; OUT=sys.argv[2]
m=WhisperModel("medium",device="cpu",compute_type="int8",cpu_threads=14)
segs,_=m.transcribe(A,language="ru",word_timestamps=True,vad_filter=False,beam_size=5,condition_on_previous_text=False)
ws=[]
for s in segs:
    for w in (s.words or []): ws.append({"w":w.word.strip(),"s":round(w.start,3),"e":round(w.end,3)})
    print("%6.2f  %s"%(s.start,s.text.strip()),flush=True)
json.dump(ws,open(OUT,"w",encoding="utf-8"),ensure_ascii=False,indent=1)
print("WORDS",len(ws),"| dur %.2f | wpm %.1f"%(ws[-1]["e"],len(ws)/(ws[-1]["e"]/60)))
