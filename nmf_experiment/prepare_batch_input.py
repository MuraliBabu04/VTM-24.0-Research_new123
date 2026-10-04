"""Materialize the first 32 frames using established repository sequence sources."""
import base64
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import urllib.request

META = {
 'B1': dict(sequence='B1_Kimono1', width=1920,height=1080,fps=24,bitdepth=8,cfg='Kimono.cfg',url='https://drive.google.com/file/d/1843eyCx362pJgZ1BWzBSPLzsqIsD4fmC/view',source_sha256='4708b443662722a081cff8eaa9fd3426be76b1f6d144c78d0d477ffd98df14c2'),
 'C1': dict(sequence='C1_RaceHorses',width=832,height=480,fps=30,bitdepth=8,cfg='RaceHorsesC.cfg',url='https://drive.google.com/file/d/1d8FMx_LEGCNSPlY5pu_o5x69Se9lZhkQ/view'),
 'D1': dict(sequence='D1_RaceHorses',width=416,height=240,fps=30,bitdepth=8,cfg='RaceHorses.cfg',source_sha256='7192decb5ab38d0367afcce4c3ca77c6fc06b11d0d50de2c27eceda8ecd24951'),
 'E1': dict(sequence='E1_FourPeople',width=1280,height=720,fps=60,bitdepth=8,cfg='FourPeople.cfg',url='https://media.xiph.org/video/derf/y4m/FourPeople_1280x720_60.y4m'),
 'A1': dict(sequence='A1_Tango2',width=3840,height=2160,fps=60,bitdepth=10,cfg='Tango2.cfg',url='https://drive.google.com/file/d/1UYRKYgN51OX1cpVHq-TCtJe-qo0YDuq1/view'),
}

def digest(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()

def read_exact(f,n):
 out=bytearray()
 while len(out)<n:
  b=f.read(n-len(out))
  if not b: raise EOFError('Input ended before 32 complete frames')
  out.extend(b)
 return out

def main(code):
 m=dict(META[code],code=code,frames=32,MTS=1,LFNST=0)
 root=Path('test_sequence');root.mkdir(exist_ok=True)
 output=root/'input.yuv'
 size=m['width']*m['height']*3//2*(2 if m['bitdepth']>8 else 1)
 if code=='A1':
  subprocess.run([sys.executable,'scripts/prepare_class_a1_tango_input.py','--url',m['url'],'--output',str(output),'--frames','32'],check=True)
 elif code=='E1':
  with urllib.request.urlopen(m['url'],timeout=120) as f, output.open('wb') as out:
   header=f.readline().decode('ascii').strip();m['source_header']=header
   tokens=header.split()
   assert tokens[0]=='YUV4MPEG2' and 'W1280' in tokens and 'H720' in tokens
   assert 'F60:1' in tokens and any(x in tokens for x in ['C420','C420jpeg','C420mpeg2','C420paldv'])
   for i in range(32):
    assert f.readline().startswith(b'FRAME'),i
    out.write(read_exact(f,size))
 else:
  with tempfile.TemporaryDirectory() as tmp:
   raw=Path(tmp)/'source.yuv'
   if code=='D1':
    parts=sorted(Path('test_sequences/class_d').glob('D1_RaceHorses_416x240_30.yuv.gz.b64.part*.b64'))
    assert len(parts)==11
    packed=Path(tmp)/'source.gz'
    with packed.open('wb') as out:
     for part in parts: out.write(base64.b64decode(part.read_bytes()))
    with gzip.open(packed,'rb') as f,raw.open('wb') as out: shutil.copyfileobj(f,out)
   else:
    subprocess.run([sys.executable,'-m','gdown',m['url'],'-O',str(raw)],check=True)
   assert raw.stat().st_size>=32*size and raw.stat().st_size%size==0
   m['source_hash_measured']=digest(raw)
   if 'source_sha256' in m: assert m['source_hash_measured']==m['source_sha256']
   with raw.open('rb') as f,output.open('wb') as out:
    for i in range(32): out.write(read_exact(f,size))
 assert output.stat().st_size==32*size
 m['input_sha256']=digest(output);m['input_bytes']=output.stat().st_size
 (root/'input.sha256').write_text(m['input_sha256']+'  test_sequence/input.yuv\n')
 (root/'metadata.json').write_text(json.dumps(m,indent=2)+'\n')
 print(json.dumps(m,indent=2))

if __name__=='__main__': main(sys.argv[1])
