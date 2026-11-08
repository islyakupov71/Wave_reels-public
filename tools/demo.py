"""Build a synthetic demo without accounts, speech recordings or network calls."""
from pathlib import Path
import importlib.util,json,subprocess,sys,wave
ROOT=Path(__file__).resolve().parents[1]
work=ROOT/'build/demo';work.mkdir(parents=True,exist_ok=True)
spec=importlib.util.spec_from_file_location('demo_scenario',ROOT/'examples/demo.py')
scenario=importlib.util.module_from_spec(spec);spec.loader.exec_module(scenario)
words=scenario.GROUND_TRUTH.split();step=4/len(words)
alignment=[{'w':word,'s':round(i*step,3),'e':round((i+1)*step,3)} for i,word in enumerate(words)]
(work/'words.json').write_text(json.dumps(alignment,ensure_ascii=False,indent=2),encoding='utf-8')
with wave.open(str(work/'silence.wav'),'wb') as audio:
    audio.setparams((1,2,48000,0,'NONE','not compressed'));audio.writeframes(b'\0'*(48000*4*2))
subprocess.run([sys.executable,str(ROOT/'engine/build2.py'),str(ROOT/'examples/demo.py'),str(work/'words.json'),'4'],cwd=ROOT,check=True)
print('Synthetic demo ready: serve this folder on localhost and open engine/out2.html')
