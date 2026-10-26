"""Analytic counterexample: trigger activation need not reduce minimum cost.

This is a constructed scalar classifier, not a BadFU/FUBA experiment.
"""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from probe import write


def triangle(x, start):
    relu=lambda a:np.maximum(a,0)
    return relu(x-start)-2*relu(x-start-.005)+relu(x-start-.01)


def score(x, post):
    return 1000*(triangle(x,.01)+(triangle(x,.04) if post else 0))-1


def main():
    out=Path(__file__).resolve().parent
    x=np.linspace(0,.001,100)
    clean_x=np.r_[x,np.full(100,.015)]
    clean_y=np.r_[np.zeros(100,dtype=int),np.ones(100,dtype=int)]
    # Exact first target interval starts at .011 (ties have infimum .011).
    pre_cost=.011-x;post_cost=.011-x
    result={'hypothesis':'고정 트리거의 성공률 상승은 최소 목표 변형 비용 감소를 필연적으로 보장한다.',
            'kind':'Analytic counterexample, not an empirical FUBA reproduction',
            'n_non_target':100,'clean_n':200,
            'clean_accuracy_pre_pct':float(np.mean((score(clean_x,False)>0)==clean_y)*100),
            'clean_accuracy_post_pct':float(np.mean((score(clean_x,True)>0)==clean_y)*100),
            'fixed_trigger':'x -> x+.044',
            'fixed_trigger_ASR_pre_pct':float(np.mean(score(x+.044,False)>0)*100),
            'fixed_trigger_ASR_post_pct':float(np.mean(score(x+.044,True)>0)*100),
            'q95_minimum_cost_pre':float(np.sort(pre_cost)[94]),
            'q95_minimum_cost_post':float(np.sort(post_cost)[94]),
            'minimum_cost_change':0.,'verdict':'기각: 신규 공격 경로보다 더 가까운 기존 오분류 경로가 남아 최소 비용은 바뀌지 않는다.',
            'does_not_prove':'All server-side detection impossible; the two classifiers differ on the new target interval.'}
    assert result['fixed_trigger_ASR_pre_pct']==0 and result['fixed_trigger_ASR_post_pct']==100
    assert np.array_equal(pre_cost,post_cost)
    write(out/'COST_COUNTEREXAMPLE.json',result)
    plt.rcParams.update({'font.family':'Malgun Gothic','axes.unicode_minus':False,'font.size':11})
    grid=np.linspace(0,.06,2001)
    fig,axes=plt.subplots(2,1,figsize=(10.5,6.6),layout='constrained',sharex=True)
    for ax,post,title in zip(axes,[False,True],['삭제 전: 기존 오분류 경로만 있음','삭제 후: 기존 경로 + 새로운 공격 경로']):
        ax.plot(grid,score(grid,post),color='#247ba0',lw=2)
        ax.axhline(0,color='gray',lw=.8)
        ax.axvspan(0,.001,color='green',alpha=.2,label='정상 입력')
        ax.axvline(.011,color='#d74e48',ls='--',label='최소 목표 변형 비용 약0.011')
        ax.axvspan(.044,.045,color='orange',alpha=.25,label='같은 공격 트리거 적용 위치')
        ax.set(title=title,ylabel='목표 클래스 점수 (양수면 목표로 분류)',ylim=(-1.6,4.6))
        ax.legend(loc='upper right',fontsize=9);ax.grid(alpha=.2)
    axes[-1].set_xlabel('입력 변형량 (정상 입력은 0 부근)')
    fig.suptitle('가설 반례: 공격 ASR 0% →100%, 정상 정확도 유지, 최소 변형 비용은 동일\n'
                 '구성한 수학적 예시이며 FUBA 실험 결과가 아님',fontsize=13)
    fig.savefig(out/'COST_COUNTEREXAMPLE_KO.png',dpi=160);plt.close(fig)
    print('COUNTEREXAMPLE_VERIFIED: ASR0to100, minimum-cost unchanged')


if __name__=='__main__':main()
