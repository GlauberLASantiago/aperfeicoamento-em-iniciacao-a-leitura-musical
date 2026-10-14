import argparse,concurrent.futures,hashlib,json,subprocess
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True);parser.add_argument('--destination',type=Path,required=True);parser.add_argument('--ffmpeg',type=Path,required=True);args=parser.parse_args()
args.destination.mkdir(exist_ok=True)
def convert(source):
    original=source.read_bytes();sha1=hashlib.sha1(original).hexdigest();out=args.destination/(sha1+'.mp4')
    if not out.exists():
        process=subprocess.run([str(args.ffmpeg),'-hide_banner','-loglevel','error','-protocol_whitelist','file,pipe','-i',str(source),'-c:v','libx264','-preset','veryfast','-crf','22','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-movflags','+faststart','-threads','2','-y',str(out)],capture_output=True,text=True,timeout=900)
        if process.returncode:raise RuntimeError(process.stderr)
    data=out.read_bytes()
    row={'source':str(source.relative_to(args.source)).replace('\\','/'),'sourceSha1':sha1,'sourceSha256':hashlib.sha256(original).hexdigest(),'sourceBytes':len(original),'mp4':out.name,'mp4Sha256':hashlib.sha256(data).hexdigest(),'mp4Bytes':len(data),'settings':'H.264 / AAC, yuv420p, CRF22, faststart; original FLV preserved'}
    print(json.dumps({'converted':row['source'],'bytes':len(data)}),flush=True);return row
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(convert,sorted(args.source.rglob('*.flv'))))
(args.destination/'conversion-manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8')
print('PASS: converted',len(rows),'videos',flush=True)
