from pathlib import Path
import os
import runpy
import sys

root=Path(__file__).resolve().parent.parent
os.environ['OMP_NUM_THREADS']='2'
os.environ['MKL_NUM_THREADS']='2'
os.environ['CUDA_VISIBLE_DEVICES']=''
sys.stdout=(root/'worker.stdout.log').open('a',encoding='utf-8',buffering=1)
sys.stderr=(root/'worker.stderr.log').open('a',encoding='utf-8',buffering=1)
sys.argv=[str(root/'sources/normal_stress.py'),'--out',str(root)]
runpy.run_path(str(root/'sources/normal_stress.py'),run_name='__main__')
