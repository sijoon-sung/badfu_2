"""Render stored public-model predictions; no new model inference or selection training."""
import json
from pathlib import Path
import torch
from torchvision.datasets import MNIST
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from prepare import ROOT, sha, write

torch.set_num_threads(1)
r=json.loads((ROOT/'DBA_RESULT.json').read_text())
assert sha(ROOT/'DBA_predictions.pt')==r['predictions_sha256']
p=torch.load(ROOT/'DBA_predictions.pt',map_location='cpu',weights_only=True)['distillation']
ds=MNIST('C:/Users/DISLAB/Documents/antigravity/dazzling-lovelace/FUBA/data',train=False,download=False)
assert torch.equal(ds.targets,p['labels'])
rows=[]
fig,axes=plt.subplots(2,6,figsize=(12,6.4))
for col,label in enumerate(range(6)):
    valid=(p['labels']==label)&(p['clean']==label)&(p['trigger']==8)
    index=int(torch.nonzero(valid)[0])
    x=ds.data[index].float()/255
    a=x.clone()
    for y0,y1,x0,x1 in [(0,2,0,5),(4,6,7,12),(0,2,7,12),(4,6,0,5)]:a[y0:y1,x0:x1]=1
    for row,img in enumerate([x,a]):
        axes[row,col].imshow(img,cmap='gray',vmin=0,vmax=1)
        axes[row,col].axis('off')
        pred=int(p['clean'][index] if row==0 else p['trigger'][index])
        axes[row,col].set_title(f'ID {index} | prediction {pred}',fontsize=9)
    rows.append({'test_index':index,'label':label,'clean_prediction':int(p['clean'][index]),'DBA_prediction':int(p['trigger'][index])})
fig.suptitle('Public author FUBA KD endpoint: clean images vs DBA trigger\nMNIST | CA 98.85% | ASR 81.14% | target 8',fontsize=13,y=.99)
fig.text(.5,.01,'Author-supplied post model only. This is not a newly trained or verified pre/post unlearning pair.',ha='center',fontsize=9)
fig.subplots_adjust(left=.02,right=.98,bottom=.09,top=.82,hspace=.32,wspace=.12)
fig.savefig(ROOT/'PUBLIC_AUTHOR_KD_EXAMPLES_v2.png',dpi=160)
write('PUBLIC_AUTHOR_KD_EXAMPLES_v2.json',{'selection':'first test ID per class 0..5 with clean correct and triggered target8',
    'example_count':6,'rows':rows,'is_random_population_sample':False,'new_model_forward_count':0,
    'image_sha256':sha(ROOT/'PUBLIC_AUTHOR_KD_EXAMPLES_v2.png'),'predictions_sha256':r['predictions_sha256']})
print(json.dumps(rows),flush=True)
