"""Render recorded FU predictions; no model loading, inference or new selection metric."""
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    root=Path(__file__).resolve().parent;payload=root/'delivery/payload'
    evidence=json.loads((payload/'INDEPENDENT_RESULT.json').read_text())
    source=payload/'predictions.npz'
    assert hashlib.sha256(source.read_bytes()).hexdigest()==evidence['predictions']['sha256']
    data=np.load(source);labels=data['labels'];clean=data['clean'];triggered=data['triggered']
    chosen=[]
    for label in range(10):
        eligible=np.flatnonzero((labels==label)&(clean==labels)&(triggered==8)&(labels!=8))
        if len(eligible):chosen.append(int(eligible[0]))
        if len(chosen)==6:break
    if not chosen:raise ValueError('No clean-correct targeted failures; do not fabricate examples')
    fig,axes=plt.subplots(2,len(chosen),figsize=(12,6.4),squeeze=False)
    for column,index in enumerate(chosen):
        image=data['images'][index];stamped=image.copy()
        for y0,y1,x0,x1 in [(0,2,0,5),(4,6,7,12),(4,6,0,5),(0,2,7,12)]:stamped[y0:y1,x0:x1]=255
        for row,im in enumerate([image,stamped]):
            ax=axes[row,column];ax.imshow(im,cmap='gray',vmin=0,vmax=255);ax.axis('off')
            pred=clean[index] if row==0 else triggered[index]
            ax.set_title(f'Label {labels[index]}\nPrediction: {pred}',fontsize=10,color='#1f2937' if row==0 else '#bd3030')
        axes[1,column].text(.5,-.08,f'Test image {index}',ha='center',va='top',transform=axes[1,column].transAxes,fontsize=9)
    fig.suptitle('Actual FUBA Retrain FU: client 4 removed',fontsize=18,y=.98)
    fig.text(.5,.90,f'After FU: clean accuracy {evidence["CA_pct"]:.2f}% | target-8 ASR {evidence["ASR_pct"]:.2f}% (all 9,026 non-target images)',ha='center',fontsize=11)
    fig.text(.5,.055,'Top: clean inputs. Bottom: global DBA trigger. Selected examples illustrate failures; the rate uses the full test set.',ha='center',fontsize=10)
    fig.text(.5,.018,'Original pre-FU ASR was 30.60%: suppression failed. This is not a completed latent-pair or whole-paper reproduction.',ha='center',fontsize=10,color='#9c2727')
    fig.subplots_adjust(top=.80,bottom=.15,wspace=.12,hspace=.52)
    path=root/'ACTUAL_RETRAIN_FU_EXAMPLES_v2.png';assert not path.exists();fig.savefig(path,dpi=180);plt.close(fig)
    receipt={'source_sha256':evidence['predictions']['sha256'],'selected_test_ids':chosen,
             'selection':'First clean-correct targeted failure per non-target class, at most six; illustration only',
             'model_loads':0,'inference':0,'figure_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    with (root/'ACTUAL_RETRAIN_FU_EXAMPLES_v2.json').open('x') as f:json.dump(receipt,f,indent=2)
    print(json.dumps(receipt))


if __name__=='__main__':main()
