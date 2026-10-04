"""Compare every completed pair; preserve partial results and explicit failures."""
import csv
import json
from pathlib import Path
import sys
from compare_exact_correction import compare

def main(stage):
 expected=[(s,q) for s in ('B1','C1','D1','E1') for q in ([22,27] if s=='B1' else [22,27,32,37])] if stage=='bcde' else [('A1',q) for q in [22,27,32,37]]
 out=Path('batch_summary');out.mkdir(exist_ok=True)
 results=[];errors=[];rows=[]
 for seq,qp in expected:
  a=Path('results')/seq/f'QP{qp}'/'anchor';p=a.parent/'proposed'
  try:
   for name in ['commit.txt','build.sha256','input.sha256','metadata.json']:
    assert (a/name).read_bytes()==(p/name).read_bytes(),f'Mismatched {name}'
   r=compare(a/'encode.log',p/'encode.log',a/'output.vvc',p/'output.vvc',qp)
   r['sequence']=seq;r['input']=json.loads((a/'metadata.json').read_text())
   r['same_runner']=False
   r['note']='Variants ran on separate GitHub hosted runners; runtime comparisons are descriptive. Dense correction does not establish power savings.'
   results.append(r)
   for variant in ['anchor','proposed']:
    v=r[variant]
    rows.append(dict(sequence=seq,qp=qp,design=variant,**{k:v.get(k) for k in ['bitrate_kbps','Y_PSNR_dB','U_PSNR_dB','V_PSNR_dB','YUV_PSNR_dB','user_seconds','elapsed_seconds']},bitstream_identical=r['bitstream_identical']))
   if not r['bitstream_identical'] or not r['reported_metrics_identical']: errors.append(dict(sequence=seq,qp=qp,error='Bitstreams or metrics differ'))
  except Exception as e: errors.append(dict(sequence=seq,qp=qp,error=str(e)))
 report=dict(stage=stage,expected_pairs=len(expected),compared_pairs=len(results),results=results,errors=errors)
 (out/f'{stage}.json').write_text(json.dumps(report,indent=2)+'\n')
 fields=['sequence','qp','design','bitrate_kbps','Y_PSNR_dB','U_PSNR_dB','V_PSNR_dB','YUV_PSNR_dB','user_seconds','elapsed_seconds','bitstream_identical']
 with (out/f'{stage}.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
 lines=['| Sequence | QP | Design | kb/s | Y | U | V | YUV | Elapsed s | Identical bits |','|---|---:|---|---:|---:|---:|---:|---:|---:|---|']
 for row in rows: lines.append('| '+' | '.join(str(row[k]) for k in ['sequence','qp','design','bitrate_kbps','Y_PSNR_dB','U_PSNR_dB','V_PSNR_dB','YUV_PSNR_dB','elapsed_seconds','bitstream_identical'])+' |')
 lines.extend(['','Errors: '+json.dumps(errors),'','Unobserved exact kernels: '+json.dumps({f"{r['sequence']}-QP{r['qp']}":r['exact_kernels_not_observed'] for r in results})])
 (out/f'{stage}.md').write_text('\n'.join(lines)+'\n')
 print(json.dumps(report,indent=2))
 if errors: raise SystemExit('Incomplete or unequal pairs; see preserved results and job logs')

if __name__=='__main__': main(sys.argv[1])
