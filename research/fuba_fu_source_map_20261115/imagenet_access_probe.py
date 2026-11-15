"""Bounded read-only ImageNet location and official HTTP-header inspection; no data download."""
import concurrent.futures
import json
from pathlib import Path
import shutil
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parent
SCOPES=[Path(x) for x in ['D:/data','D:/datasets','D:/imagenet','D:/ImageNet','D:/tmpfs','D:/ILSVRC2012',
    'C:/Users/DISLAB/Downloads','C:/Users/DISLAB/datasets','C:/Users/DISLAB/data',
    'C:/Users/DISLAB/.cache/huggingface/datasets']]


def probe(name):
    url='https://image-net.org/data/ILSVRC/2012/'+name
    try:
        request=urllib.request.Request(url,method='HEAD')
        with urllib.request.urlopen(request,timeout=10) as response:
            return {'url':url,'status':response.status,'content_length':response.headers.get('Content-Length'),
                'content_type':response.headers.get('Content-Type'),'final_url':response.url,'body_bytes_read':0}
    except urllib.error.HTTPError as e:return {'url':url,'status':e.code,'body_bytes_read':0}
    except Exception as e:return {'url':url,'error':type(e).__name__+': '+str(e),'body_bytes_read':0}


def main():
    scopes=[];matches=[]
    for base in SCOPES:
        record={'path':str(base),'exists':base.exists(),'max_depth':2};scopes.append(record)
        if not base.is_dir():continue
        queue=[(base,0)];seen=0
        while queue and seen<10000:
            parent,depth=queue.pop(0)
            try:children=list(parent.iterdir())
            except OSError:continue
            for p in children:
                seen+=1
                if any(word in p.name.lower() for word in ['imagenet','ilsvrc']):
                    matches.append({'path':str(p),'directory':p.is_dir(),'bytes':p.stat().st_size if p.is_file() else None})
                if p.is_dir() and not p.is_symlink() and depth<1:queue.append((p,depth+1))
        record['entries_seen']=seen;record['entry_cap_reached']=seen>=10000
    names=['ILSVRC2012_img_train.tar','ILSVRC2012_img_val.tar','ILSVRC2012_devkit_t12.tar.gz']
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:headers=list(pool.map(probe,names))
    result={'state':'read_only_probe_complete','official_download_page':'https://www.image-net.org/challenges/LSVRC/2012/2012-downloads.php',
        'scopes':scopes,'matches':matches,'official_headers':headers,'image_data_downloaded_bytes':0,
        'disk_free_bytes':{drive:shutil.disk_usage(drive).free for drive in ['C:/','D:/']},
        'absence_outside_scopes_not_proven':True,'model_training_or_inference':0}
    with (ROOT/'IMAGENET_ACCESS_PROBE.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
