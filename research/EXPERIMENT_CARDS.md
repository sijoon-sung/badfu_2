# 실험 카드 — 가설·정상 대조·실패 이유

[먼저 연구 인덱스 읽기](INDEX.md) · [전체 폴더](EXPERIMENT_FOLDERS.md)

기존 대표 보고서와 정정을 재검토한 카드에 2026-10-25 사용자 요청의 별도 고정 모델 진단(D18)을 추가 연결. 카드별 원문과 실행/수학/사후진단 범위를 구분한다. 인덱스 생성 자체는 모델 재계산을 수행하지 않는다.

가설은 색인을 위한 한 줄 요약이며 새 사전등록이 아니다. 원 보고서의 개별 가설·프로토콜·판정 범위를 우선한다.

<a id="r01"></a>

## R01 · 승인된 BadFU 모델과 삭제 방식

**가설 한 줄: 승인된 체크포인트의 출처와 삭제 집합을 확인하면 탐지 실험의 전후 모델을 일관되게 선택할 수 있다.**

**판정: 검증 범위 한정**

[실험 시작 이유와 실제 실행 과정 읽기](../experiments/01-reproduction/R01-badfu-reproduction/README.md)

- **조건:** Paper32 전체 이력과 확정 시드20261023 끝점; SHA256 및 payload_key 확인. 원본 경로 보존.
- **정상 대조·비교:** 정상850삭제와 큰 정상 참여자 삭제를 별도 조건으로 보관.
- **결과:** 최종 모델 기본 ID는 badfu.confirmed.s20261023.v1, 전체 이력은 badfu.paper32.s20261020. 저장 검증·공격 재현·삭제 방식은 별도 판정이다.
- **non-IID에 대해 남길 교훈:** 모델 보관·재현 검증 통과는 정상 non-IID와 공격의 구별 성공을 뜻하지 않는다.
- **반복하지 않을 주장:** 유지 자료 전체 재학습을 근사 FedEraser라고 부르거나 파일명·높은 ASR로 모델을 고르지 않는다.
- **재검토 조건:** select_case.py로 명시적 용도를 선택하고 선언된 해시·형식을 확인한다.

**원문·증거:**

- [research/00_trajectories/README.md](00_trajectories/README.md)
- [research/00_trajectories/catalog.json](00_trajectories/catalog.json)
- [research/badfu_algorithm_audit_20261023/README.md](badfu_algorithm_audit_20261023/README.md)

**묶은 폴더:** [00_trajectories](00_trajectories) · [badfu_algorithm_audit_20261023](badfu_algorithm_audit_20261023) · [confirmed_checkpoint_20261023](confirmed_checkpoint_20261023) · [CONFIRMED_CHECKPOINTS](../CONFIRMED_CHECKPOINTS)

<a id="r02"></a>

## R02 · FUBA 재현 실패와 평가 혼동

**가설 한 줄: 생성기 상태와 평가 경로를 바로잡으면 FUBA의 삭제 전 억제·삭제 후 활성화가 재현된다.**

**판정: FUBA 두완료실패 보존 / 사용자 FedUBA 대상정정으로 나머지queue중지**

[실험 시작 이유와 실제 실행 과정 읽기](../experiments/01-reproduction/R02-fuba-reproduction/README.md)

- **조건:** stcebra/FUBA 수정 후보와 과거 보존 모델; ity207/FedUBA와 다른 연구.
- **정상 대조·비교:** 같은 생성기를 정상 모델에도 적용한 교차 진단; 정상 삭제 대조의 완료 여부 별도 확인.
- **결과:** 승인된 잠복 활성화 전후쌍은 없다. 기존 정상 모델로의 높은 생성기 전이 기록을 보존한다. v2 시드20261023은100R 저장·연결·집계 오차0·186개 작업자 생성기 그룹 검증 및 로컬 복사를 완료했으나, 전체10000장 정확도71.87%/타깃 제외9000장 ASR99.0889%로 사전 억제10% 기준을 실패했다. 진단 전용 삭제 전 모델이며 후속 대조·삭제는 실행하지 않았다. 저장·회귀검사 통과를 공격 재현 성공으로 세지 않는다. 2026-10-24 원문·실행 감사에서 재가중 방향·억제2단계 입력·단계 순서·가상 집계/γ 실패 처리·학습 조건 불일치를 확인했고 별도 수정 후보의 CPU 회귀15개가 통과했다. 고정 저장 모델 추론에서 로컬 억제와 전체 집계 실패를 구분했다. IBA 결합/프로필 질문과 실자료 재현은 미검증이며 새 학습은 시작하지 않았다. 2026-10-24 사용자 재실행 지시에 따라 공식 소스를 재확보·대조하고 별도 v3 프로필의 DISLAB100R을 시작했다. 추가CPU9개와 실제GPU/MPI20제출·집계오차0·CPU출력 검사를 통과했다. 검사 fixture의 ASR은 억제 증거가 아니며 본 학습 결과는 미완료다. IBA 결합/BN 정책은 명시한 구현 선택으로 고정했고 과거 실패는 보존한다. 2026-10-24 v3는15R 저장 후16R 참여자1의 γ0 로컬 ASR12.9464%(29/224) 실패로 등록 규칙에 따라 중단했다. 15R 전체10000/9000장 독립 재평가는 CA76.10%/ASR8.1333%로 기록과 일치했다. 전체15R 해시·연결·집계 오차0·120개 역할·13개 G그룹을 검증하고, 마지막15R·실패16R·소스·평가 사본을 로컬에 봉인 전달했다.100R 미완료·CA80% 미달이며 잠복 전후쌍/재현 성공이 아니다. 자동 재시작·정상/삭제 분기는 실행하지 않았다. 2026-10-24 사용자 재지시에 따라 별도 v4 제어흐름 프로필로 DISLAB16–100R 연속 실행을 시작했다. 본문Algorithm1 lines9–12의 γ0 반환과 달리v3에 추가했던 whole-MPI 종료를 고쳤고, γ0의 BN 변경도 막았다. 로컬 실패12.9464%는 같은 저장G/모델로 독립 재현하고 미달 상태 그대로 기록했다. 원래 완료된16R client1 학습 단계는 원본 기록과 함께 재사용하고 나머지 실제 학습을 수행한다. 수치·시드·최종100R/CA80/ASR10 기준은 유지하며 중간ASR 경보를 성공으로 표시하지 않는다. 원본 실패/사본은 보존한다. 본 실행 결과는 아직 미완료다. 새16R은15→16 연결·집계 오차0·γ0 실제 제출·같은G·CPU출력 검증을 통과했고 전체시험 평가 기록은CA76.86%/ASR9.3778%다. 최종100R 결과 또는 독립 재평가는 아니다. v4의17–19R 전체시험ASR12.0444/11.5444/12.8333%로 최초 연속 경보가 발생했다. 19R 모델/로그를 별도 보존하고3R의 파일·연결·정확집계0·24역할·4개G그룹 및 고정320/288장 CPU 추론을 검증했다. 17R은 로컬 예상9.5455% 통과 후 실제 전체집계12.0444%였고,3R 모두 억제 참여자가 미선택됐다. 19R 두γ0 제출의 항등성도 통과했다. 예상/실제 집계 간 실패 경로이며 개별 원인의 인과 분리는 미완료다. 원본 v4 학습/최종 기준은 유지하고 새로운 학습·자동 재시작은 하지 않았다. 최종100R은 미완료다. v4는23R 저장 후24R client3의선언gamma상한10에서중단했다. 전체23R/184역할/28G그룹/정확집계0이통과했고 독립10000/9000평가CA77.12%/ASR13.9444%를재현했다. 원본cap분기가중간모델/점수를저장하지못한결함을확인하고별도저장보강CPU검사를통과했다. 사용자승인단일참여자진단은원본G그대로/4단계50epoch였으나gamma2.0통과/2.1실패로원본cap10을재현하지못했다. 마지막23R·원본실패·단계모델·진단을별도봉인하여로컬전달했다.100R은미완료이며원본FL재개/상한확대/다른참여자실행은하지않았다. 2026-10-24 최신100R완료재지시에따라별도v5를사전등록했다.23R동일해시복원후24–100R을계산하며cap10은유지하고최대값미확정의마지막검사통과값을제출해전체FL을계속한다.원본실패/진단은보존하고진단모델을재사용하지않는다.모든학습조건과최종100R/CA80/ASR10은유지하며실행결과는미완료다. v5실제MPI/GPU학습시작과23R복원/집계0/엄격CPU검사를확인했고자동확인fuba-v5-100이최종100R검증·로컬전달까지이어간다.진행중이며최종성공은미확정이다. v5첫24R저장과23→24연결/8역할/집계오차0/같은G/단계RNG6개/소스해시가통과했고25R학습을이어간다.24R기록CA75.48/ASR13.3444는중간미달로보존하며최종100R독립평가성공으로세지않는다. v5의31R효용은gamma10제출후CA10.19/ASR0으로급락했다.원본연결/8역할/집계오차0/실제상한제출동일성이통과했고모델·점수·소스를별도보존했다.ASR0을억제성공으로보지않으며개별인과기여분리는미완료다.원조건을바꾸지않고100R계속실행중이다. 2026-10-25 v5최종100R완료와전체파일/연결/800역할/186G그룹/집계오차0/948단계RNG를검증했다. 독립10000/9000평가CA78.58%/pre-ASR28.6889%가기록과정확히일치해CA80/ASR10게이트는실패했다.32–100R공격자111회는모두로컬gamma0미달/zero제출이었다.완료모델·소스·평가·cap/RNG/31R효용실패·감독복구근거를양쪽봉인전달하고해시/CPU로드/출력을확인했다.단일삭제전진단모델이며잠복전후쌍은없고추가학습/정상/FU를자동시작하지않았다. 2026-10-25 사용자 삭제후 직접 실행 재지시:100R 전달만으로 전체목표를종료한범위를정정하고,원본v5를보존한별도KD-based FU10회로참여자4의실제이력기여제거/무라벨KD/전후pt·로그·고정G평가를사전등록했다.공개코드배열위치/20대신실제ID/weights를연결하고supplementary의10회/clean무라벨KD를따르는정정을명시했다.사전ASR실패를이유로FU실행을생략하지않으며성능성공은미확정이다. 2026-10-25 KD-based FU 실제10회/400batch를완료하고삭제후.pt·전체로그·전후쌍을양쪽보존했다.전CA78.58/ASR28.68888888888889,후CA78.95/ASR28.42222222222222이며동일G전체독립평가가일치했다.실제전후쌍은존재하지만사전억제실패로잠복재현성공은아니다.원문/공개코드정정을기록했고원본v5봉인본은불변이다. 2026-10-25 최신 DISLAB 정상코드 직접 재지시:공개commit/10파일과실제함수를DISLAB에서재검사했다.기존v5가이미고친공개코드결함과새수식SGD/Adam차이를구분하며m4정정은확정하지않았다.저장100R의추가BN보정은로컬gamma0미달을바꾸지않았다.별도v6프로필에서명시된2개업데이트만literalSGD/다른단계Adam및학습BN정책을사전선언하고fresh100R→실제KD10→전후pt/전체로그/독립검증을일회성으로시작했다.로컬·DISLABCPU계약9개와실제학습PID/GPU진행을확인했고실행코드26파일/동일해시/최초CPU출력을로컬전달했다.최종100R/KD10/성능재현은아직미완료이며저자공인유일해석으로부르지않는다.모든원본실패는보존한다. v6첫1R실저장검사:초기모델연결/실제8역할·각50epoch2000배치/400epoch로그/정확집계0의CPU검사가통과했고이후라운드를계속한다.최종100R·KD10성능재현은아직미완료다. v6첫6R방어자계약검사:실제6R의유일한악성역할client4에서4단계각50epoch/1800batch,optimizer Adam·Adam·SGD·SGD,실제G5epoch와동일G보존,unscaled기준최종제출식및집계오차0을CPU검사했다.6R에는Adv-attacker가선택되지않아gamma계약을검사했다고하지않는다.7R학습은계속하며최종재현은미완료다. v6첫7R공격자계약검사:client0의4단계각50epoch/1800batch,Adam·Adam·SGD·Adam,동일G/실제제출/집계0이CPU검사통과했다.최초gamma0로컬ASR10.909090909090908미달로정확한zero제출을확인했으며양수gamma선택통과나점수독립재계산이라고하지않는다.실제7R전체CA70.69/ASR4.222222222222222는중간기록이며최종성공이아니다.8R이후원조건학습을계속한다. 2026-10-26 즉시개입 감사:63R의504역할/전체epoch로그/고정소스23해시를대조했고,실제제출·집계/G·optimizer/RNG 텐서검사를확대했다.28R까지통과후감사stdout OSError22는학습오류와분리보존하고영속로그의별도CPU관측작업으로바로복구했다.9R선택gamma2.3은18/220동일하지만탈락2.4에서CPU24/220대GPU23/220의1장불일치를발견하여원본보존·수치진단중이며전체독립점수통과라고하지않는다.52R cap점수두개는같았다.원래trainer가실제100R+KD10/400batch를완료했고전CA77.8/ASR12.811111111111112,후CA78.03/ASR14.544444444444444로최종성능게이트는미달이다.별도CPU검사로client4의실제41기여가중합·차감·KD10/400고유배치/25000예시·최종상태일치를확인했다.전체100R검증·동일GPU독립평가·로컬전후모델전달은계속한다.다른GPU앱점유로유휴guard가막은것을관측했으며다른앱종료/유휴기준우회/학습재시작은하지않았다. v6보강CPU100R감사완료:100R/800역할/186악성G그룹/1235모델산출파일의해시·연결·optimizer/RNG·제출식·집계0과전체epoch로그/23소스검사를통과했다.관측프로세스는정상종료했다.공격자146회에서zero미달91/첫실패경계36/cap19,양수제출55다.모든gamma독립추론이나원래FINAL_VERIFIED/전체GPU독립평가/로컬전후모델전달완료는아니다.1장CPU/GPU점수차이는보존하며최종검증·전달을계속한다. v6실제전후모델로컬중간보존:PENDING_FINAL_MODELS에실제before/after/fixedG와전체epoch/KD로그등13파일의동일해시·CPU엄격로드/출력을확인했다.수집기소스경로오류는보존·정정했고학습/원격모델은불변이다.최종검토패킷·독립평가·전체KD모델전달·카탈로그guard는미완료이며자동확인을유지한다. v6원래전체CPU검증도100R/800역할/186G/744단계/집계0/KD10·400고유배치/2304파일을통과했다.이후GPU812MiB유휴guard로독립평가가CUDA추론전에실패했고원래감독·평가PID종료/중복평가부재를확인했다.원래실패·로그·소스11파일을양쪽동일해시로보존하고GPU자원결정을요청했다.실제GPU유휴후평가·export만복구하며학습재실행이나기준우회는하지않는다.전체독립평가·최종검토패킷·카탈로그는미완료다. 2026-10-31 사용자는 기존 stcebra/FUBA를 우선하고 논문 Algorithm1/2 일치를 최종 기준으로 재확정했다. 이전 원코드 기반 실행·수정 이력이 없었다는 설명을 정정했다. 별도 고정100R/client1·학습된 previousG99/같은 incoming·앵커·RNG/50개 epoch 데이터순서에서 embedding SGD 대 Adam만 실제50epoch씩 비교했다. 총100epoch/3600batch, 전체10000/9000 평가에서 SGD CA72.97/ASR.6777778, Adam CA72.43/ASR1.7444444로20%p 개선 가설 미지지. 기존 v7 최종전후 지표와 다른 로컬 진단이다. 새A는 원래phase3와 비트 불일치이므로 현재runtime A/B로 한정한다. 새4모델 파일/optimizer/RNG/전체로그 CPU검증과 로컬 해시 전달을 완료했고 새100R/FU·탐지 실행은 하지 않았다. Algorithm1/2 함수 대응과 gamma/BN/IBA 통합의 미확정 선택을 구분했으며 Adam을 정식 알고리즘으로 채택하지 않았다. 모든 기존 실패·카탈로그·기본값을 보존했다. 2026-10-31 학습반경만 .05로 맞춘 같은50epoch/1800batch 진단은CA56.06/ASR84.7222222/정상타깃쏠림37.5888889로효용/쏠림게이트를실패했다. 모델/optimizer/RNG/로그를검증·전달했고전체IBA일정을자동실행하지않았다. 별도논문내MNIST/DBA기준선은원공개BN없는Net/고정패치로Algorithm1/2 fresh100R후실제KD10을사전등록했다. DISLABCPU8계약·데이터/소스/초기모델해시·실제trainer/controller/GPU와첫정상50epoch/2350batch저장계약을통과했고실제학습중이다. CIFAR/IBA재현성공이나탐지성공으로대체하지않으며최종100R/KD10·성능·전달은미완료다. 첫실제악성역할을포함한별도CPU7R감사는56역할/65phase/3250epoch/150350batch,Adam/SGD·RNG,실제제출수식/8명정확집계/연결과11점gamma선택산술을통과했다. 전체gamma독립재추론/최종100R성공은아니다. 2026-10-31 MNIST/DBA 실제100R/800역할/1358phase·67900epoch·3042500batch와KD10/470을완료했다. 독립10000/9026평가가전CA99.11/ASR30.600487480611566,후CA99.08/ASR32.35098604032794에정확일치해두성능게이트는미달이다. 실제client4기여41개·정확차감,146gamma선택산술/미달zero2,전체CPU감사와69payload strictCPU/finiteforward를통과했다. 선택모델과전체로그984파일을양쪽봉인전달하고모든sha/양쪽catalogueguard를확인했다. 새case fuba.reference.mnist.dba.s20261023.pre100.post.kd10은diagnostic만허용하며기존case/default/audit를보존했다. 전체원시phase는DISLAB에보존한다. 성공재현/탐지증거가아니며전체구현목표는미완료다. 별도stage19상태진단에서차감직후CA98.88/ASR68.3691557722136였고KD10후32.35098604여서등록된KD약화가설이지지됐다. 검증전후정수수는재사용했고새학습/모델편집은없다. 삭제전30.6005실패와실제KD10후실패는남고성공한잠복쌍은아니다. local패치validation/global합집합의행동차이를관측했지만감마수정의전체FL성공은미검증이다. 고정두역할의22global gamma검사에서100R local9.8113/global58.1132의scope위반은확인했다. 단일round zero대체집계는CA99.07/ASR16.09794로사전10기준을못넘어이수정하나의전체실행게이트는실패했다. 개선과음성을보존하고별도마지막억제자99/client4 recovery SGD/Adam100epoch비교를사전등록했다. 다른CIFAR embedding optimizer실패를다시실행하거나Adam동일수식으로부르지않는다. 마지막억제자99/client4 recovery의새SGD50epoch/2150batch는원래phase4 tensorbit재현gate를실패해B를실행하지않고중단했다. optimizer/loader·CPU·CUDA RNG는같고최대수치차이8.94e-08이지만원인은미확정이다. 이실패를보존하며입력bit일치/행동1%p gate를통과할때만미실행B50epoch를처음학습하는별도current-runtime비교를등록했다. A를재학습하거나strictbit실패를통과로고치지않는다. 별도current-runtime후속은입력bit/loader RNG/원phase4대A행동일치를통과하고A를재훈련하지않은채B50epoch/2150batch만최초학습했다. recovered ASR은A98.26058/B98.00576,실제99R대체집계는37.00421/36.58320으로두기준을실패해optimizer만으로전체학습을열지않는다. 실제A/B모델·optimizer/RNG·로그를전달했다. 2026-10-31 recovery의strict-bit 대조는8.94e-08 비트차이로실패를보존했다. 입력/loader RNG/전체평가정수수동일gate를별도통과한현재runtime B-only Adam50epoch/2150batch는SGD회복ASR98.26058 대Adam98.00576으로20%p 개선gate에실패했고실제99R대체집계도37.00421/36.58320으로10에못미쳤다. Adam/global-gamma 선택을채택하지않는다. 논문10random-seed 평균의필요조건을확인하는별도고정10행study를사전등록했다. 완료실패seed20261023을포함하고미리추출한새9개를같은Algorithm-SGD 수치코드/새초기화·IID분할/실제100R/KD10으로DISLAB에서순차계산한다. 성공시중단/실패seed제외/목록확장은금지한다. 현재준비단계이며최종성능은미측정이다. 본문Adam 실험프로필의정확재현이나D08/D15 탐지해결이아니다. 새9개CPU준비는통과했으나첫seed5129832 launch가3epoch 뒤실제PID와예약작업이사라져중단됐다. 완료phase/round는0이고종료원인은미확정이다. 원상태/3epoch/소스·입력을보존한별도운영복구는동일initial/SPLIT/숫자코드를새attempt경로에복사했다. 직접Python action을쓰는명시복구계약이며wrapper원인을확정하지않는다. 직접Python 운영복구후실제세PID/첫50epoch/3개round커밋과4R진행을확인했다. 별도첫1R CPU8역할/400epoch/18800batch·정확집계·optimizer/RNG검사가통과했다. 현재MNIST4개공식MD5/압축해제바이트도통과했다. warmup검사이며최종100R/KD10·악성성능·10행평균은미완료다. 새6R의48역할/54phase/2700epoch/125300batch,실제attacker1/defender1 제출식·정확집계·optimizer/RNG·11점gamma선택산술1개도CPU감사통과했다. 전체gamma독립추론이나최종재현성공은아니다. 첫새seed5129832의실제100R/800역할/1394phase/69700epoch·3117500batch와client4실제47기여차감/KD10/470을완료했다. 독립10000/9026평가전CA99.12/ASR23.000221582096167,후CA99.15/ASR29.016175493020164로두게이트미달이며152gamma선택산술/전체CPU감사와양쪽readonly982파일·로컬74payload strictCPU/세catalogueguard가통과했다. case fuba.algorithm_sgd.mnist.dba.s5129832.pre100.post.kd10.seed_repro20261031은diagnostic만허용한다. 기존case/default/audit를보존했다. baseline포함10행중2개완료이며다음seed4059094는GPU진입자원조건을기다린다. source/성능조건은변경하지않고기존parent가순차계속한다. 최신사용자가FedUBA(SSS/BEA)로대상을명시정정하여기존대기queue만중지·비활성화했다. 실제대기상태/own PID48688/task action을확인했고다른앱은종료하지않았다. 두완료실패행과나머지8미시작및모든원본·defaults는보존했으며10행을완료한것은아니다.
- **non-IID에 대해 남길 교훈:** 부적합한 FUBA 전후쌍에서의 점수 겹침은 유효한 잠복 FUBA에 대한 불가능성 증명이 아니다.
- **반복하지 않을 주장:** 높은 ASR만으로 공격 양성을 정하거나 과거 README의 진행 중 문장을 현재 GPU 상태로 보고하지 않는다.
- **재검토 조건:** 같은 실행·고정 생성기·전처리·효용을 연결한 재현 게이트와 정상 대조부터 통과해야 한다.

**원문·증거:**

- [research/00_trajectories/README.md](00_trajectories/README.md)
- [research/continuation_20261023/README.md](continuation_20261023/README.md)
- [research/asr_root_cause_20261022/REPORT_KO.md](asr_root_cause_20261022/REPORT_KO.md)
- [research/rapid_checkpoint_validation_20261023/REPORT_KO.txt](rapid_checkpoint_validation_20261023/REPORT_KO.txt)
- [research/fuba_checkpoint_recovery_20261023/README.md](fuba_checkpoint_recovery_20261023/README.md)
- [research/fuba_checkpoint_recovery_20261023/PARTIAL_LOCAL_round0063.json](fuba_checkpoint_recovery_20261023/PARTIAL_LOCAL_round0063.json)
- [CHECKPOINTS_FOR_REVIEW/FUBA_v2_s20261023_round0063/README.md](../CHECKPOINTS_FOR_REVIEW/FUBA_v2_s20261023_round0063/README.md)
- [research/fuba_checkpoint_recovery_20261023/PENDING82_RECOVERED.json](fuba_checkpoint_recovery_20261023/PENDING82_RECOVERED.json)
- [research/fuba_checkpoint_recovery_20261023/RESUMED_ROUND0083_VERIFIED.json](fuba_checkpoint_recovery_20261023/RESUMED_ROUND0083_VERIFIED.json)
- [research/fuba_checkpoint_recovery_20261023/STORAGE_RESUME_PLAN.json](fuba_checkpoint_recovery_20261023/STORAGE_RESUME_PLAN.json)
- [research/fuba_checkpoint_recovery_20261023/LOCAL_COPY_COMPLETE.json](fuba_checkpoint_recovery_20261023/LOCAL_COPY_COMPLETE.json)
- [research/fuba_checkpoint_recovery_20261023/FINAL_EVALUATOR_LINKAGE.json](fuba_checkpoint_recovery_20261023/FINAL_EVALUATOR_LINKAGE.json)
- [research/00_trajectories/audit/FUBA_V2_ROUND100_DELIVERY.json](00_trajectories/audit/FUBA_V2_ROUND100_DELIVERY.json)
- [CHECKPOINTS_FOR_REVIEW/FUBA_v2_s20261023_pre_round100/README.md](../CHECKPOINTS_FOR_REVIEW/FUBA_v2_s20261023_pre_round100/README.md)
- [research/fuba_suppression_audit_20261024/REPORT_KO.txt](fuba_suppression_audit_20261024/REPORT_KO.txt)
- [research/fuba_suppression_audit_20261024/FIXES_PROVENANCE.json](fuba_suppression_audit_20261024/FIXES_PROVENANCE.json)
- [research/fuba_suppression_audit_20261024/REGRESSION_RESULTS.json](fuba_suppression_audit_20261024/REGRESSION_RESULTS.json)
- [research/fuba_suppression_audit_20261024/RECORDED_ROLE_EVALUATION.json](fuba_suppression_audit_20261024/RECORDED_ROLE_EVALUATION.json)
- [research/fuba_suppression_audit_20261024/GAMMA_ZERO_IDENTITY.json](fuba_suppression_audit_20261024/GAMMA_ZERO_IDENTITY.json)
- [research/fuba_suppression_audit_20261024/CODE_REVIEW_REMOTE.json](fuba_suppression_audit_20261024/CODE_REVIEW_REMOTE.json)
- [research/fuba_paper_rebuild_20261024/PROTOCOL.txt](fuba_paper_rebuild_20261024/PROTOCOL.txt)
- [research/fuba_paper_rebuild_20261024/PROFILE.json](fuba_paper_rebuild_20261024/PROFILE.json)
- [research/fuba_paper_rebuild_20261024/REPORT_KO.txt](fuba_paper_rebuild_20261024/REPORT_KO.txt)
- [research/fuba_paper_rebuild_20261024/OFFICIAL_SOURCES.json](fuba_paper_rebuild_20261024/OFFICIAL_SOURCES.json)
- [research/fuba_paper_rebuild_20261024/SOURCE_INSPECTION.json](fuba_paper_rebuild_20261024/SOURCE_INSPECTION.json)
- [research/fuba_paper_rebuild_20261024/CPU_TESTS.json](fuba_paper_rebuild_20261024/CPU_TESTS.json)
- [research/fuba_paper_rebuild_20261024/SMOKE_VERIFIED.json](fuba_paper_rebuild_20261024/SMOKE_VERIFIED.json)
- [research/fuba_paper_rebuild_20261024/READY.json](fuba_paper_rebuild_20261024/READY.json)
- [research/fuba_paper_rebuild_20261024/LAUNCH.json](fuba_paper_rebuild_20261024/LAUNCH.json)
- [research/fuba_paper_rebuild_20261024/FIRST_MAIN_CHECKPOINT_VERIFIED.json](fuba_paper_rebuild_20261024/FIRST_MAIN_CHECKPOINT_VERIFIED.json)
- [research/fuba_paper_rebuild_20261024/TERMINAL_REPORT_KO.txt](fuba_paper_rebuild_20261024/TERMINAL_REPORT_KO.txt)
- [research/fuba_paper_rebuild_20261024/TERMINAL_PREFIX_VERIFIED.json](fuba_paper_rebuild_20261024/TERMINAL_PREFIX_VERIFIED.json)
- [research/fuba_paper_rebuild_20261024/TERMINAL_INDEPENDENT_EVALUATION.json](fuba_paper_rebuild_20261024/TERMINAL_INDEPENDENT_EVALUATION.json)
- [research/fuba_paper_rebuild_20261024/EXPORT_TERMINAL_READY.json](fuba_paper_rebuild_20261024/EXPORT_TERMINAL_READY.json)
- [research/fuba_paper_rebuild_20261024/TERMINAL_LOCAL_COPY_COMPLETE.json](fuba_paper_rebuild_20261024/TERMINAL_LOCAL_COPY_COMPLETE.json)
- [research/fuba_paper_rebuild_20261024/TERMINAL_SELECTION_CHECK.json](fuba_paper_rebuild_20261024/TERMINAL_SELECTION_CHECK.json)
- [research/fuba_paper_rebuild_20261024/TERMINAL_REMOTE_NAVIGATION.json](fuba_paper_rebuild_20261024/TERMINAL_REMOTE_NAVIGATION.json)
- [research/00_trajectories/audit/FUBA_V3_STOPPED15_DELIVERY.json](00_trajectories/audit/FUBA_V3_STOPPED15_DELIVERY.json)
- [CHECKPOINTS_FOR_REVIEW/FUBA_v3_s20261023_pre_round0015_stopped_verified/README.md](../CHECKPOINTS_FOR_REVIEW/FUBA_v3_s20261023_pre_round0015_stopped_verified/README.md)
- [research/fuba_paper_flow_20261024/PROTOCOL.txt](fuba_paper_flow_20261024/PROTOCOL.txt)
- [research/fuba_paper_flow_20261024/PROFILE.json](fuba_paper_flow_20261024/PROFILE.json)
- [research/fuba_paper_flow_20261024/PAPER_COMPARISON.txt](fuba_paper_flow_20261024/PAPER_COMPARISON.txt)
- [research/fuba_paper_flow_20261024/REPORT_KO.txt](fuba_paper_flow_20261024/REPORT_KO.txt)
- [research/fuba_paper_flow_20261024/CPU_TESTS.json](fuba_paper_flow_20261024/CPU_TESTS.json)
- [research/fuba_paper_flow_20261024/PREFLIGHT.json](fuba_paper_flow_20261024/PREFLIGHT.json)
- [research/fuba_paper_flow_20261024/READY.json](fuba_paper_flow_20261024/READY.json)
- [research/fuba_paper_flow_20261024/LAUNCH.json](fuba_paper_flow_20261024/LAUNCH.json)
- [research/fuba_paper_flow_20261024/FOLLOWUP.json](fuba_paper_flow_20261024/FOLLOWUP.json)
- [research/fuba_paper_flow_20261024/attack_100R/RESUME_RESTORED.json](fuba_paper_flow_20261024/attack_100R/RESUME_RESTORED.json)
- [research/fuba_paper_flow_20261024/FIRST_CONTINUED_ROUND_VERIFIED.json](fuba_paper_flow_20261024/FIRST_CONTINUED_ROUND_VERIFIED.json)
- [research/fuba_paper_flow_20261024/ASR_ALERT19_PROTOCOL.txt](fuba_paper_flow_20261024/ASR_ALERT19_PROTOCOL.txt)
- [research/fuba_paper_flow_20261024/ASR_ALERT19_REPORT_KO.txt](fuba_paper_flow_20261024/ASR_ALERT19_REPORT_KO.txt)
- [research/fuba_paper_flow_20261024/attack_100R/ASR_ALERT_round0019.json](fuba_paper_flow_20261024/attack_100R/ASR_ALERT_round0019.json)
- [research/fuba_paper_flow_20261024/alert_diagnostics_round0019/DIAGNOSIS.json](fuba_paper_flow_20261024/alert_diagnostics_round0019/DIAGNOSIS.json)
- [research/fuba_paper_flow_20261024/alert_diagnostics_round0019/SUBMITTED_DIAGNOSIS.json](fuba_paper_flow_20261024/alert_diagnostics_round0019/SUBMITTED_DIAGNOSIS.json)
- [research/fuba_paper_flow_20261024/alert_diagnostics_round0019/PRESERVED.json](fuba_paper_flow_20261024/alert_diagnostics_round0019/PRESERVED.json)
- [research/fuba_paper_flow_20261024/TERMINAL23_REPORT_KO.txt](fuba_paper_flow_20261024/TERMINAL23_REPORT_KO.txt)
- [research/fuba_paper_flow_20261024/CAP24_DIAGNOSIS_REPORT_KO.txt](fuba_paper_flow_20261024/CAP24_DIAGNOSIS_REPORT_KO.txt)
- [research/fuba_paper_flow_20261024/CAP24_DIAGNOSIS_REPORT_KO_v1.txt](fuba_paper_flow_20261024/CAP24_DIAGNOSIS_REPORT_KO_v1.txt)
- [research/fuba_paper_flow_20261024/CAP24_REPORT_ERRATUM.txt](fuba_paper_flow_20261024/CAP24_REPORT_ERRATUM.txt)
- [research/fuba_paper_flow_20261024/TERMINAL23_PREFIX_VERIFIED.json](fuba_paper_flow_20261024/TERMINAL23_PREFIX_VERIFIED.json)
- [research/fuba_paper_flow_20261024/TERMINAL23_INDEPENDENT_EVALUATION.json](fuba_paper_flow_20261024/TERMINAL23_INDEPENDENT_EVALUATION.json)
- [research/fuba_paper_flow_20261024/EXPORT23_READY.json](fuba_paper_flow_20261024/EXPORT23_READY.json)
- [research/fuba_paper_flow_20261024/TERMINAL23_LOCAL_COPY_COMPLETE.json](fuba_paper_flow_20261024/TERMINAL23_LOCAL_COPY_COMPLETE.json)
- [research/fuba_paper_flow_20261024/TERMINAL23_SELECTION_CHECK.json](fuba_paper_flow_20261024/TERMINAL23_SELECTION_CHECK.json)
- [research/fuba_paper_flow_20261024/CAP24_INSPECTION.json](fuba_paper_flow_20261024/CAP24_INSPECTION.json)
- [research/fuba_paper_flow_20261024/CAP24_REPLAY_PROTOCOL.txt](fuba_paper_flow_20261024/CAP24_REPLAY_PROTOCOL.txt)
- [research/fuba_paper_flow_20261024/CAP24_CACHED_G_REPLAY_PROTOCOL.txt](fuba_paper_flow_20261024/CAP24_CACHED_G_REPLAY_PROTOCOL.txt)
- [research/fuba_paper_flow_20261024/CACHED_G_RNG_CPU_TEST.json](fuba_paper_flow_20261024/CACHED_G_RNG_CPU_TEST.json)
- [research/fuba_paper_flow_20261024/cap24_diagnostic_candidate/PROFILE.json](fuba_paper_flow_20261024/cap24_diagnostic_candidate/PROFILE.json)
- [research/fuba_paper_flow_20261024/cap24_diagnostic_candidate/CPU_TESTS.json](fuba_paper_flow_20261024/cap24_diagnostic_candidate/CPU_TESTS.json)
- [research/fuba_paper_flow_20261024/cap24_replay_20261024/STATE.json](fuba_paper_flow_20261024/cap24_replay_20261024/STATE.json)
- [research/fuba_paper_flow_20261024/cap24_replay_cached_G_20261024/RESULT.json](fuba_paper_flow_20261024/cap24_replay_cached_G_20261024/RESULT.json)
- [research/fuba_paper_flow_20261024/cap24_replay_cached_G_20261024/GENERATOR_REPLAY_EXACT.json](fuba_paper_flow_20261024/cap24_replay_cached_G_20261024/GENERATOR_REPLAY_EXACT.json)
- [research/00_trajectories/audit/FUBA_V4_STOPPED23_DELIVERY.json](00_trajectories/audit/FUBA_V4_STOPPED23_DELIVERY.json)
- [CHECKPOINTS_FOR_REVIEW/FUBA_v4_s20261023_pre_round0023_stopped_verified/README.txt](../CHECKPOINTS_FOR_REVIEW/FUBA_v4_s20261023_pre_round0023_stopped_verified/README.txt)
- [research/fuba_paper_completion_20261024/PROTOCOL.txt](fuba_paper_completion_20261024/PROTOCOL.txt)
- [research/fuba_paper_completion_20261024/PROFILE.json](fuba_paper_completion_20261024/PROFILE.json)
- [research/fuba_paper_completion_20261024/PAPER_COMPARISON.txt](fuba_paper_completion_20261024/PAPER_COMPARISON.txt)
- [research/fuba_paper_completion_20261024/REPORT_KO.txt](fuba_paper_completion_20261024/REPORT_KO.txt)
- [research/fuba_paper_completion_20261024/CPU_TESTS.json](fuba_paper_completion_20261024/CPU_TESTS.json)
- [research/fuba_paper_completion_20261024/SOURCE_CASE_SELECTION.json](fuba_paper_completion_20261024/SOURCE_CASE_SELECTION.json)
- [research/fuba_paper_completion_20261024/LAUNCH.json](fuba_paper_completion_20261024/LAUNCH.json)
- [research/fuba_paper_completion_20261024/PREFLIGHT.json](fuba_paper_completion_20261024/PREFLIGHT.json)
- [research/fuba_paper_completion_20261024/READY.json](fuba_paper_completion_20261024/READY.json)
- [research/fuba_paper_completion_20261024/FOLLOWUP.json](fuba_paper_completion_20261024/FOLLOWUP.json)
- [research/fuba_paper_completion_20261024/FIRST_ATTACKER24_VERIFIED.json](fuba_paper_completion_20261024/FIRST_ATTACKER24_VERIFIED.json)
- [research/fuba_paper_completion_20261024/FIRST_ROUND24_VERIFIED.json](fuba_paper_completion_20261024/FIRST_ROUND24_VERIFIED.json)
- [research/fuba_paper_completion_20261024/cap_capture_verification/round0031_client03.json](fuba_paper_completion_20261024/cap_capture_verification/round0031_client03.json)
- [research/fuba_paper_completion_20261024/UTILITY31_REPORT_KO.txt](fuba_paper_completion_20261024/UTILITY31_REPORT_KO.txt)
- [research/fuba_paper_completion_20261024/utility_round0031/AUDIT.json](fuba_paper_completion_20261024/utility_round0031/AUDIT.json)
- [research/fuba_paper_completion_20261024/SUPERVISION_RECOVERY_PROTOCOL.txt](fuba_paper_completion_20261024/SUPERVISION_RECOVERY_PROTOCOL.txt)
- [research/fuba_paper_completion_20261024/SUPERVISION_RECOVERY_REPORT_KO.txt](fuba_paper_completion_20261024/SUPERVISION_RECOVERY_REPORT_KO.txt)
- [research/fuba_paper_completion_20261024/SUPERVISION_CPU_TESTS.json](fuba_paper_completion_20261024/SUPERVISION_CPU_TESTS.json)
- [research/fuba_paper_completion_20261024/SUPERVISOR_RECOVERY_VERIFIED.json](fuba_paper_completion_20261024/SUPERVISOR_RECOVERY_VERIFIED.json)
- [research/fuba_paper_completion_20261024/SUPERVISOR_RECOVERY_LAUNCH.json](fuba_paper_completion_20261024/SUPERVISOR_RECOVERY_LAUNCH.json)
- [research/fuba_paper_completion_20261024/FINAL_VERIFIED.json](fuba_paper_completion_20261024/FINAL_VERIFIED.json)
- [research/fuba_paper_completion_20261024/FINAL_INDEPENDENT_EVALUATION.json](fuba_paper_completion_20261024/FINAL_INDEPENDENT_EVALUATION.json)
- [research/fuba_paper_completion_20261024/FINAL_ROLE_STATISTICS.json](fuba_paper_completion_20261024/FINAL_ROLE_STATISTICS.json)
- [research/fuba_paper_completion_20261024/FINAL_REPORT_KO.txt](fuba_paper_completion_20261024/FINAL_REPORT_KO.txt)
- [research/fuba_paper_completion_20261024/FINAL_PAPER_COMPARISON.txt](fuba_paper_completion_20261024/FINAL_PAPER_COMPARISON.txt)
- [research/fuba_paper_completion_20261024/EXPORT100_READY.json](fuba_paper_completion_20261024/EXPORT100_READY.json)
- [research/fuba_paper_completion_20261024/ROUND100_LOCAL_COPY_COMPLETE.json](fuba_paper_completion_20261024/ROUND100_LOCAL_COPY_COMPLETE.json)
- [research/fuba_paper_completion_20261024/ROUND100_SELECTION_CHECK.json](fuba_paper_completion_20261024/ROUND100_SELECTION_CHECK.json)
- [research/00_trajectories/audit/FUBA_V5_ROUND100_DELIVERY.json](00_trajectories/audit/FUBA_V5_ROUND100_DELIVERY.json)
- [CHECKPOINTS_FOR_REVIEW/FUBA_v5_s20261023_pre_round100/README.txt](../CHECKPOINTS_FOR_REVIEW/FUBA_v5_s20261023_pre_round100/README.txt)
- [research/fuba_paper_completion_20261024/DELIVERY_REPORT_KO.txt](fuba_paper_completion_20261024/DELIVERY_REPORT_KO.txt)
- [research/fuba_paper_completion_20261024/ROUND100_REMOTE_NAVIGATION.json](fuba_paper_completion_20261024/ROUND100_REMOTE_NAVIGATION.json)
- [research/fuba_post_unlearning_20261025/PROTOCOL.txt](fuba_post_unlearning_20261025/PROTOCOL.txt)
- [research/fuba_post_unlearning_20261025/PROFILE.json](fuba_post_unlearning_20261025/PROFILE.json)
- [research/fuba_post_unlearning_20261025/CPU_TESTS.json](fuba_post_unlearning_20261025/CPU_TESTS.json)
- [research/fuba_post_unlearning_20261025/PREFLIGHT.json](fuba_post_unlearning_20261025/PREFLIGHT.json)
- [research/fuba_post_unlearning_20261025/LAUNCH.json](fuba_post_unlearning_20261025/LAUNCH.json)
- [research/fuba_post_unlearning_20261025/RESULT.json](fuba_post_unlearning_20261025/RESULT.json)
- [research/fuba_post_unlearning_20261025/INDEPENDENT_FINAL.json](fuba_post_unlearning_20261025/INDEPENDENT_FINAL.json)
- [research/fuba_post_unlearning_20261025/REPORT_KO.txt](fuba_post_unlearning_20261025/REPORT_KO.txt)
- [research/fuba_post_unlearning_20261025/EXPORT_READY.json](fuba_post_unlearning_20261025/EXPORT_READY.json)
- [research/fuba_post_unlearning_20261025/LOCAL_COPY_COMPLETE.json](fuba_post_unlearning_20261025/LOCAL_COPY_COMPLETE.json)
- [research/fuba_post_unlearning_20261025/SELECTION_CHECK.json](fuba_post_unlearning_20261025/SELECTION_CHECK.json)
- [research/fuba_post_unlearning_20261025/LOG_VERIFIED.json](fuba_post_unlearning_20261025/LOG_VERIFIED.json)
- [research/00_trajectories/audit/FUBA_V5_KD10_PAIR_DELIVERY.json](00_trajectories/audit/FUBA_V5_KD10_PAIR_DELIVERY.json)
- [CHECKPOINTS_FOR_REVIEW/FUBA_v5_s20261023_pre100_post_KD10/README.txt](../CHECKPOINTS_FOR_REVIEW/FUBA_v5_s20261023_pre100_post_KD10/README.txt)
- [research/fuba_post_unlearning_20261025/REMOTE_NAVIGATION.json](fuba_post_unlearning_20261025/REMOTE_NAVIGATION.json)
- [research/fuba_post_unlearning_20261025/incidents/local_model_import/INCIDENT.json](fuba_post_unlearning_20261025/incidents/local_model_import/INCIDENT.json)
- [research/fuba_execution_audit_20261025/PROTOCOL.txt](fuba_execution_audit_20261025/PROTOCOL.txt)
- [research/fuba_execution_audit_20261025/SOURCE_AUDIT.json](fuba_execution_audit_20261025/SOURCE_AUDIT.json)
- [research/fuba_execution_audit_20261025/SCORE_PROBE.json](fuba_execution_audit_20261025/SCORE_PROBE.json)
- [research/fuba_algorithm_execution_20261025/PROTOCOL.txt](fuba_algorithm_execution_20261025/PROTOCOL.txt)
- [research/fuba_algorithm_execution_20261025/PROFILE.json](fuba_algorithm_execution_20261025/PROFILE.json)
- [research/fuba_algorithm_execution_20261025/REPORT_KO.txt](fuba_algorithm_execution_20261025/REPORT_KO.txt)
- [research/fuba_algorithm_execution_20261025/CPU_TESTS.json](fuba_algorithm_execution_20261025/CPU_TESTS.json)
- [research/fuba_algorithm_execution_20261025/READY.json](fuba_algorithm_execution_20261025/READY.json)
- [research/fuba_algorithm_execution_20261025/LOCAL_EXECUTED_CODE_VERIFIED.json](fuba_algorithm_execution_20261025/LOCAL_EXECUTED_CODE_VERIFIED.json)
- [research/fuba_algorithm_execution_20261025/FIRST_ROUND_VERIFIED.json](fuba_algorithm_execution_20261025/FIRST_ROUND_VERIFIED.json)
- [research/fuba_algorithm_execution_20261025/FIRST_MALICIOUS_VERIFIED.json](fuba_algorithm_execution_20261025/FIRST_MALICIOUS_VERIFIED.json)
- [research/fuba_algorithm_execution_20261025/FIRST_ATTACKER_VERIFIED.json](fuba_algorithm_execution_20261025/FIRST_ATTACKER_VERIFIED.json)
- [research/fuba_algorithm_execution_20261025/LIVE_AUDIT_PROTOCOL.txt](fuba_algorithm_execution_20261025/LIVE_AUDIT_PROTOCOL.txt)
- [research/fuba_algorithm_execution_20261025/LIVE_AUDIT_REPORT_KO.txt](fuba_algorithm_execution_20261025/LIVE_AUDIT_REPORT_KO.txt)
- [research/fuba_algorithm_execution_20261025/live_audit/SCORE_PROBE.json](fuba_algorithm_execution_20261025/live_audit/SCORE_PROBE.json)
- [research/fuba_algorithm_execution_20261025/POST_AUDIT.json](fuba_algorithm_execution_20261025/POST_AUDIT.json)
- [research/fuba_algorithm_execution_20261025/RESULT.json](fuba_algorithm_execution_20261025/RESULT.json)
- [research/fuba_algorithm_execution_20261025/live_audit/OBSERVATION_ERROR_1792953931211524800.json](fuba_algorithm_execution_20261025/live_audit/OBSERVATION_ERROR_1792953931211524800.json)
- [research/fuba_algorithm_execution_20261025/live_audit/SCORE_DIFFERENCE_DIAGNOSIS.json](fuba_algorithm_execution_20261025/live_audit/SCORE_DIFFERENCE_DIAGNOSIS.json)
- [research/fuba_algorithm_execution_20261025/live_audit/GPU_IDLE_BLOCKED_1792982419857.json](fuba_algorithm_execution_20261025/live_audit/GPU_IDLE_BLOCKED_1792982419857.json)
- [research/fuba_algorithm_execution_20261025/LIVE_PREFIX100_VERIFIED.json](fuba_algorithm_execution_20261025/LIVE_PREFIX100_VERIFIED.json)
- [research/fuba_algorithm_execution_20261025/STAGED_ENDPOINTS_VERIFIED.json](fuba_algorithm_execution_20261025/STAGED_ENDPOINTS_VERIFIED.json)
- [research/fuba_algorithm_execution_20261025/STAGING_SOURCE_PATH_CORRECTION.json](fuba_algorithm_execution_20261025/STAGING_SOURCE_PATH_CORRECTION.json)
- [research/fuba_algorithm_execution_20261025/FINAL_VERIFIED.json](fuba_algorithm_execution_20261025/FINAL_VERIFIED.json)
- [research/fuba_algorithm_execution_20261025/EVALUATION_RESOURCE_BLOCK_REPORT_KO.txt](fuba_algorithm_execution_20261025/EVALUATION_RESOURCE_BLOCK_REPORT_KO.txt)
- [research/fuba_algorithm_execution_20261025/incidents/independent_gpu_idle_1792986211065/PRESERVATION.json](fuba_algorithm_execution_20261025/incidents/independent_gpu_idle_1792986211065/PRESERVATION.json)
- [research/fuba_optimizer_isolation_20261031/PROTOCOL.txt](fuba_optimizer_isolation_20261031/PROTOCOL.txt)
- [research/fuba_optimizer_isolation_20261031/PROFILE.json](fuba_optimizer_isolation_20261031/PROFILE.json)
- [research/fuba_optimizer_isolation_20261031/IDENTITY_AND_SCOPE.txt](fuba_optimizer_isolation_20261031/IDENTITY_AND_SCOPE.txt)
- [research/fuba_optimizer_isolation_20261031/PAPER_ALGORITHM_CONTRACT.txt](fuba_optimizer_isolation_20261031/PAPER_ALGORITHM_CONTRACT.txt)
- [research/fuba_optimizer_isolation_20261031/REPORT_KO.txt](fuba_optimizer_isolation_20261031/REPORT_KO.txt)
- [research/fuba_optimizer_isolation_20261031/CPU_CONTRACTS.json](fuba_optimizer_isolation_20261031/CPU_CONTRACTS.json)
- [research/fuba_optimizer_isolation_20261031/INPUT_CHECKS.json](fuba_optimizer_isolation_20261031/INPUT_CHECKS.json)
- [research/fuba_optimizer_isolation_20261031/RESULT.json](fuba_optimizer_isolation_20261031/RESULT.json)
- [research/fuba_optimizer_isolation_20261031/VERIFIED.json](fuba_optimizer_isolation_20261031/VERIFIED.json)
- [research/fuba_optimizer_isolation_20261031/LAUNCH_CORRECTION.txt](fuba_optimizer_isolation_20261031/LAUNCH_CORRECTION.txt)
- [research/fuba_radius_alignment_20261031/PROTOCOL.txt](fuba_radius_alignment_20261031/PROTOCOL.txt)
- [research/fuba_radius_alignment_20261031/PROFILE.json](fuba_radius_alignment_20261031/PROFILE.json)
- [research/fuba_radius_alignment_20261031/RESULT.json](fuba_radius_alignment_20261031/RESULT.json)
- [research/fuba_radius_alignment_20261031/VERIFIED.json](fuba_radius_alignment_20261031/VERIFIED.json)
- [research/fuba_radius_alignment_20261031/DELIVERY.json](fuba_radius_alignment_20261031/DELIVERY.json)
- [research/fuba_radius_alignment_20261031/REPORT_KO.txt](fuba_radius_alignment_20261031/REPORT_KO.txt)
- [research/fuba_reference_mnist_dba_20261031/PROTOCOL.txt](fuba_reference_mnist_dba_20261031/PROTOCOL.txt)
- [research/fuba_reference_mnist_dba_20261031/PROFILE.json](fuba_reference_mnist_dba_20261031/PROFILE.json)
- [research/fuba_reference_mnist_dba_20261031/REPORT_KO.txt](fuba_reference_mnist_dba_20261031/REPORT_KO.txt)
- [research/fuba_reference_mnist_dba_20261031/CPU_CONTRACTS.json](fuba_reference_mnist_dba_20261031/CPU_CONTRACTS.json)
- [research/fuba_reference_mnist_dba_20261031/FIRST_ROLE_VERIFIED.json](fuba_reference_mnist_dba_20261031/FIRST_ROLE_VERIFIED.json)
- [research/fuba_reference_mnist_dba_20261031/CPU_AUDIT_through0006.json](fuba_reference_mnist_dba_20261031/CPU_AUDIT_through0006.json)
- [research/fuba_reference_mnist_dba_20261031/CPU_AUDIT_through0007.json](fuba_reference_mnist_dba_20261031/CPU_AUDIT_through0007.json)
- [research/fuba_reference_mnist_dba_20261031/MONITOR_PROTOCOL.txt](fuba_reference_mnist_dba_20261031/MONITOR_PROTOCOL.txt)
- [research/fuba_reference_mnist_dba_20261031/DELIVERY_PROTOCOL.txt](fuba_reference_mnist_dba_20261031/DELIVERY_PROTOCOL.txt)
- [research/fuba_reference_mnist_dba_20261031/DELIVERY_SOURCE_FREEZE.json](fuba_reference_mnist_dba_20261031/DELIVERY_SOURCE_FREEZE.json)
- [research/fuba_reference_mnist_dba_20261031/FINAL_REPORT_KO.txt](fuba_reference_mnist_dba_20261031/FINAL_REPORT_KO.txt)
- [research/fuba_reference_mnist_dba_20261031/RESULT.json](fuba_reference_mnist_dba_20261031/RESULT.json)
- [research/fuba_reference_mnist_dba_20261031/VERIFIED.json](fuba_reference_mnist_dba_20261031/VERIFIED.json)
- [research/fuba_reference_mnist_dba_20261031/CPU_AUDIT_through0100.json](fuba_reference_mnist_dba_20261031/CPU_AUDIT_through0100.json)
- [research/fuba_reference_mnist_dba_20261031/REMOTE_REVIEW_RECEIPT.json](fuba_reference_mnist_dba_20261031/REMOTE_REVIEW_RECEIPT.json)
- [research/fuba_reference_mnist_dba_20261031/LOCAL_DELIVERY.json](fuba_reference_mnist_dba_20261031/LOCAL_DELIVERY.json)
- [research/fuba_reference_mnist_dba_20261031/CATALOG_ENTRY.json](fuba_reference_mnist_dba_20261031/CATALOG_ENTRY.json)
- [research/fuba_reference_mnist_dba_20261031/CATALOG_AUDIT.json](fuba_reference_mnist_dba_20261031/CATALOG_AUDIT.json)
- [research/fuba_reference_mnist_dba_20261031/CATALOG_GUARD_LOCAL.json](fuba_reference_mnist_dba_20261031/CATALOG_GUARD_LOCAL.json)
- [research/fuba_reference_mnist_dba_20261031/FINAL_COMPLETION.json](fuba_reference_mnist_dba_20261031/FINAL_COMPLETION.json)
- [research/fuba_stage_localization_20261031/PROTOCOL.txt](fuba_stage_localization_20261031/PROTOCOL.txt)
- [research/fuba_stage_localization_20261031/PROFILE.json](fuba_stage_localization_20261031/PROFILE.json)
- [research/fuba_stage_localization_20261031/FREEZE.json](fuba_stage_localization_20261031/FREEZE.json)
- [research/fuba_stage_localization_20261031/RESULT.json](fuba_stage_localization_20261031/RESULT.json)
- [research/fuba_stage_localization_20261031/REPORT_KO.txt](fuba_stage_localization_20261031/REPORT_KO.txt)
- [research/fuba_stage_localization_20261031/STARTED.json](fuba_stage_localization_20261031/STARTED.json)
- [research/fuba_dba_gamma_scope_20261031/PROTOCOL.txt](fuba_dba_gamma_scope_20261031/PROTOCOL.txt)
- [research/fuba_dba_gamma_scope_20261031/PROFILE.json](fuba_dba_gamma_scope_20261031/PROFILE.json)
- [research/fuba_dba_gamma_scope_20261031/FREEZE.json](fuba_dba_gamma_scope_20261031/FREEZE.json)
- [research/fuba_dba_gamma_scope_20261031/RESULT.json](fuba_dba_gamma_scope_20261031/RESULT.json)
- [research/fuba_dba_gamma_scope_20261031/REPORT_KO.txt](fuba_dba_gamma_scope_20261031/REPORT_KO.txt)
- [research/fuba_defender_recovery_20261031/PROTOCOL.txt](fuba_defender_recovery_20261031/PROTOCOL.txt)
- [research/fuba_defender_recovery_20261031/PROFILE.json](fuba_defender_recovery_20261031/PROFILE.json)
- [research/fuba_defender_recovery_20261031/FREEZE.json](fuba_defender_recovery_20261031/FREEZE.json)
- [research/fuba_defender_recovery_20261031/CONTROL.json](fuba_defender_recovery_20261031/CONTROL.json)
- [research/fuba_defender_recovery_20261031/FAILURE.json](fuba_defender_recovery_20261031/FAILURE.json)
- [research/fuba_defender_recovery_20261031/NUMERICAL_TRIAGE.json](fuba_defender_recovery_20261031/NUMERICAL_TRIAGE.json)
- [research/fuba_defender_recovery_20261031/REPORT_KO.txt](fuba_defender_recovery_20261031/REPORT_KO.txt)
- [research/fuba_recovery_current_ab_20261031/PROTOCOL.txt](fuba_recovery_current_ab_20261031/PROTOCOL.txt)
- [research/fuba_recovery_current_ab_20261031/PROFILE.json](fuba_recovery_current_ab_20261031/PROFILE.json)
- [research/fuba_recovery_current_ab_20261031/FREEZE.json](fuba_recovery_current_ab_20261031/FREEZE.json)
- [research/fuba_recovery_current_ab_20261031/RESULT.json](fuba_recovery_current_ab_20261031/RESULT.json)
- [research/fuba_recovery_current_ab_20261031/CONTROL_PREFLIGHT.json](fuba_recovery_current_ab_20261031/CONTROL_PREFLIGHT.json)
- [research/fuba_recovery_current_ab_20261031/LOCAL_DELIVERY.json](fuba_recovery_current_ab_20261031/LOCAL_DELIVERY.json)
- [research/fuba_recovery_current_ab_20261031/REPORT_KO.txt](fuba_recovery_current_ab_20261031/REPORT_KO.txt)
- [research/fuba_seed_repro_20261031/PROFILE.json](fuba_seed_repro_20261031/PROFILE.json)
- [research/fuba_seed_repro_20261031/PROTOCOL.txt](fuba_seed_repro_20261031/PROTOCOL.txt)
- [research/fuba_seed_repro_20261031/MONITOR_PROTOCOL.txt](fuba_seed_repro_20261031/MONITOR_PROTOCOL.txt)
- [research/fuba_seed_repro_20261031/STUDY_FREEZE.json](fuba_seed_repro_20261031/STUDY_FREEZE.json)
- [research/fuba_seed_repro_20261031/PREPARED.json](fuba_seed_repro_20261031/PREPARED.json)
- [research/fuba_seed_repro_20261031/PREPARATION_AUDIT.json](fuba_seed_repro_20261031/PREPARATION_AUDIT.json)
- [research/fuba_seed_repro_20261031/STORAGE_CONTRACT.json](fuba_seed_repro_20261031/STORAGE_CONTRACT.json)
- [research/fuba_seed_repro_20261031/PREPARATION_RECEIPT.json](fuba_seed_repro_20261031/PREPARATION_RECEIPT.json)
- [research/fuba_seed_repro_20261031/REPORT_KO.txt](fuba_seed_repro_20261031/REPORT_KO.txt)
- [research/fuba_seed_repro_20261031/LAUNCH_RECOVERY_PROTOCOL.txt](fuba_seed_repro_20261031/LAUNCH_RECOVERY_PROTOCOL.txt)
- [research/fuba_seed_repro_20261031/PRELAUNCH_INCIDENT.json](fuba_seed_repro_20261031/PRELAUNCH_INCIDENT.json)
- [research/fuba_seed_repro_20261031/LAUNCH_RECOVERY_READY.json](fuba_seed_repro_20261031/LAUNCH_RECOVERY_READY.json)
- [research/fuba_seed_repro_20261031/RECOVERY_PREPARE_V1_FAILURE.json](fuba_seed_repro_20261031/RECOVERY_PREPARE_V1_FAILURE.json)
- [research/fuba_seed_repro_20261031/REMOTE_SNAPSHOT_AFTER_RECOVERY.json](fuba_seed_repro_20261031/REMOTE_SNAPSHOT_AFTER_RECOVERY.json)
- [research/fuba_seed_repro_20261031/LIVE_EXECUTION_VERIFIED.json](fuba_seed_repro_20261031/LIVE_EXECUTION_VERIFIED.json)
- [research/fuba_seed_repro_20261031/TASK_EXECUTION_VERIFIED.json](fuba_seed_repro_20261031/TASK_EXECUTION_VERIFIED.json)
- [research/fuba_seed_repro_20261031/FIRST_NEW_ROUND_CPU_AUDIT.json](fuba_seed_repro_20261031/FIRST_NEW_ROUND_CPU_AUDIT.json)
- [research/fuba_seed_repro_20261031/DATASET_AUDIT.json](fuba_seed_repro_20261031/DATASET_AUDIT.json)
- [research/fuba_seed_repro_20261031/FIRST_NEW_MALICIOUS_ROUND_CPU_AUDIT.json](fuba_seed_repro_20261031/FIRST_NEW_MALICIOUS_ROUND_CPU_AUDIT.json)
- [research/fuba_seed_repro_20261031/DELIVERY_PROTOCOL.txt](fuba_seed_repro_20261031/DELIVERY_PROTOCOL.txt)
- [research/fuba_seed_repro_20261031/deliveries/seed_5129832/RESULT.json](fuba_seed_repro_20261031/deliveries/seed_5129832/RESULT.json)
- [research/fuba_seed_repro_20261031/deliveries/seed_5129832/VERIFIED.json](fuba_seed_repro_20261031/deliveries/seed_5129832/VERIFIED.json)
- [research/fuba_seed_repro_20261031/deliveries/seed_5129832/CPU_AUDIT_through0100.json](fuba_seed_repro_20261031/deliveries/seed_5129832/CPU_AUDIT_through0100.json)
- [research/fuba_seed_repro_20261031/deliveries/seed_5129832/LOCAL_DELIVERY.json](fuba_seed_repro_20261031/deliveries/seed_5129832/LOCAL_DELIVERY.json)
- [research/fuba_seed_repro_20261031/deliveries/seed_5129832/REMOTE_DELIVERY.json](fuba_seed_repro_20261031/deliveries/seed_5129832/REMOTE_DELIVERY.json)
- [research/fuba_seed_repro_20261031/deliveries/seed_5129832/CATALOG_ENTRY.json](fuba_seed_repro_20261031/deliveries/seed_5129832/CATALOG_ENTRY.json)
- [research/fuba_seed_repro_20261031/deliveries/seed_5129832/CATALOG_AUDIT.json](fuba_seed_repro_20261031/deliveries/seed_5129832/CATALOG_AUDIT.json)
- [research/fuba_seed_repro_20261031/deliveries/seed_5129832/CATALOG_GUARD_main.json](fuba_seed_repro_20261031/deliveries/seed_5129832/CATALOG_GUARD_main.json)
- [research/fuba_seed_repro_20261031/deliveries/seed_5129832/CATALOG_GUARD_pr.json](fuba_seed_repro_20261031/deliveries/seed_5129832/CATALOG_GUARD_pr.json)
- [research/fuba_seed_repro_20261031/deliveries/seed_5129832/CATALOG_GUARD_dislab.json](fuba_seed_repro_20261031/deliveries/seed_5129832/CATALOG_GUARD_dislab.json)
- [research/fuba_seed_repro_20261031/deliveries/seed_5129832/DELIVERY_COMPLETE.json](fuba_seed_repro_20261031/deliveries/seed_5129832/DELIVERY_COMPLETE.json)
- [research/fuba_seed_repro_20261031/deliveries/seed_5129832/REPORT_KO.txt](fuba_seed_repro_20261031/deliveries/seed_5129832/REPORT_KO.txt)
- [research/00_trajectories/audit/FUBA_SEED_REPRO_S5129832_20261031_DELIVERY.json](00_trajectories/audit/FUBA_SEED_REPRO_S5129832_20261031_DELIVERY.json)
- [research/feduba_paper_implementation_20261031/PREVIOUS_QUEUE_STOPPED.json](feduba_paper_implementation_20261031/PREVIOUS_QUEUE_STOPPED.json)

**묶은 폴더:** [asr_root_cause_20261022](asr_root_cause_20261022) · [fuba_corrected_20261022](fuba_corrected_20261022) · [continuation_20261023](continuation_20261023) · [multiseed_actual_fu_20261022](multiseed_actual_fu_20261022) · [FU_gpu20261020](FU_gpu20261020) · [MOVE_TO_DISLAB_20261021](MOVE_TO_DISLAB_20261021) · [stage1_fresh_20261020](stage1_fresh_20261020) · [fuba_checkpoint_recovery_20261023](fuba_checkpoint_recovery_20261023) · [FUBA_v2_s20261023_round0063](../CHECKPOINTS_FOR_REVIEW/FUBA_v2_s20261023_round0063) · [FUBA_v2_s20261023_pre_round100](../CHECKPOINTS_FOR_REVIEW/FUBA_v2_s20261023_pre_round100) · [fuba_suppression_audit_20261024](fuba_suppression_audit_20261024) · [fuba_paper_rebuild_20261024](fuba_paper_rebuild_20261024) · [FUBA_v3_s20261023_pre_round0015_stopped_verified](../CHECKPOINTS_FOR_REVIEW/FUBA_v3_s20261023_pre_round0015_stopped_verified) · [fuba_paper_flow_20261024](fuba_paper_flow_20261024) · [FUBA_v4_s20261023_pre_round0023_stopped_verified](../CHECKPOINTS_FOR_REVIEW/FUBA_v4_s20261023_pre_round0023_stopped_verified) · [fuba_paper_completion_20261024](fuba_paper_completion_20261024) · [FUBA_v5_s20261023_pre_round100](../CHECKPOINTS_FOR_REVIEW/FUBA_v5_s20261023_pre_round100) · [fuba_post_unlearning_20261025](fuba_post_unlearning_20261025) · [FUBA_v5_s20261023_pre100_post_KD10](../CHECKPOINTS_FOR_REVIEW/FUBA_v5_s20261023_pre100_post_KD10) · [fuba_execution_audit_20261025](fuba_execution_audit_20261025) · [fuba_algorithm_execution_20261025](fuba_algorithm_execution_20261025) · [fuba_optimizer_isolation_20261031](fuba_optimizer_isolation_20261031) · [fuba_radius_alignment_20261031](fuba_radius_alignment_20261031) · [fuba_reference_mnist_dba_20261031](fuba_reference_mnist_dba_20261031) · [fuba_stage_localization_20261031](fuba_stage_localization_20261031) · [fuba_dba_gamma_scope_20261031](fuba_dba_gamma_scope_20261031) · [fuba_defender_recovery_20261031](fuba_defender_recovery_20261031) · [fuba_recovery_current_ab_20261031](fuba_recovery_current_ab_20261031) · [fuba_seed_repro_20261031](fuba_seed_repro_20261031)

<a id="r03"></a>

## R03 · FedUBA 공식 배포본·논문 대응과 표본 정체 감사

**가설 한 줄: 공식 FedUBA 배포본이 논문의 실행 절차와 표본 정체를 보존하여 탐지 검증에 쓸 실제 공격 전후쌍을 제공한다.**

**판정: positive ASR58.7444·4성능gate실패 / 별도 독립확인서 복구완료·원실패보존**

[실험 시작 이유와 실제 실행 과정 읽기](../experiments/01-reproduction/R03-feduba-reproduction/README.md)

- **조건:** ity207/FedUBA@005959ab8a955f4dcf094930ce6953af8fee827b와 저자 PDF/ZIP; DISLAB CPU 원본 import 및 AST 함수 실행. stcebra/FUBA 모델과 구별.
- **정상 대조·비교:** 같은 합성32샘플의 shuffled batch1 대 sequential batch1; 고정 Arguments의 FL/FU 소유권 대 보조자료 helper 소유권; 저자 ZIP 대 Git blob.
- **결과:** 저자 ZIP9파일 모두 고정 Git blob과 동일. 두 원본 import는 utils/models 부재로 종료1. 민감도 순회 위치를 데이터 ID로 재사용하는 경로의 합성 순위 일치0/32 대 순차 대조32/32; 실제 FL/FU 공격자5/7 대 보조자료2/3 불일치 확인. 실제 공격 FL/FU·CA/ASR·탐지율은 생성하지 않았다. 논문-코드 조건과 평가 정의 차이를 기록하고 G0/G1에서 전체 학습 진입을 중단했다. 이것은 실제 공격 성공률이나 논문 공격 불가능성의 증명이 아니다. 최신사용자가SSS/BEA의FedUBA구현을명시하여기존FUBA우선지시를대체했다. 기존FUBA대기parent48688과정확예약작업만상태/정체검사후중지·비활성화했고두완료실패/8미시작과모든모델/default를보존했다. 새별도원문식5~8·stable ID/소유권·정확budget·x-delta요청/x+delta평가·실제FedEraser수식 core와새DISLAB CPU계약을준비했다. 누락모델은동일ResNet18/201기호의Narcissus고정코드를명시회복후보로선정했으며저자누락파일과동일하다고인증하지않았다. 실제FL/FU성능은아직미측정이다. 새명시core의DISLAB CPU6계약이실제통과했다(CORE_CPU_RESULT). 원64표본ID/analytic score·정확소유예산·BEA부호/라벨·원AST FU·복구모델10/201 CPU·투영trigger1step이며실공격성능은아니다. 새고정20RcleanFLfoundation의fixture/실제200역할/독립검증계약을게시했다. 게시commit a9acbec 뒤GPUfixture실제통과(peak1010/984MiB)·공식CIFAR MD5/새initial·분할준비후 parent35368/controller9492/trainer54660으로freshcleanFL20을1회시작했고첫두역할전체10epoch를확인했다. 실제20R완료·최종CA·FedUBA ASR은아직없다. 외부자료CPU준비첫task는다운로드/OUT생성전CUDA가능여부assert에서중단됐다. 원task/source/freeze/trace를incident에보존하고GPU가보이는지와CPU수행을분리하는fresh-child진단·명시CPU2운영복구계약을게시했다. cleanFL은중단/재학습하지않았다. 빈CUDA값에서availableTrue/device_count0/미초기화/CPU tensor를진단하고-1로명시CPU2복구했다. 원실패보존. CPU2에서Tiny100000/200x500·CRC 및고정Git CIFAR10.1v6 2000/target200 준비·victimtrain/test exact중복각0을실측완료했다. 새literalSGD평균gradient/투영·고정theta/BN·입력clip·외부dataset의DISLAB CPU4계약도통과했다. STG_PROFILE은미실행/launchfalse이며fullSTG·SSS·공격/정상FU는아직남는다. 별도동일수치STG_LAUNCH_PROFILE/전체runner·audit·sourcefreeze를5df1852에선게시후새STG controller34020을1회시작했다. fresh외부surrogate CPU준비STG_READY는실제통과했으며cleanFL20 독립검증/효용·원foundation종료/자원guard대기다. 실제STG GPU학습이나78410batch완료를주장하지않는다. 구준비profile은불변이다. 새FU_PROFILE/paired-data·owner5/7·동적batch·variableparticipants/first-round effective-history 정책을게시후DISLAB 새CPU4계약통과했다. 기존core/원AST반복이나실SSS/FU실행이아니다. FU launchfalse·actual20R case등록/선택과STG완료/감사는아직필요하다. 새SSS logger 합성61 CPUv1은decimal poly의analytic식 atol1e-7 검사에서실패했고원source/freeze/trace발췌를보존했다. 실victim/SSS/FU실행은없다. 사후허용치확대대신별도primitive roundoff진단·binary-exact 분모128/정확동일CPU2계약을준비했다. 원logger/core/실실험허용치는불변이다. SSS fulllogger/runner/독립audit 코드추가·실SSS미실행. v1소수합성fixture상쇄오차1.043e-7을별도primitive진단으로확인하고원실패보존. logger/core/실실험허용치는불변인채분모128 binary-exact CPU2의정확torch.equal/새4계약이실제통과했다. 실SSS launchprofile/freeze는아직없고source-only freeze로검토가능하게했다. fullFU공유engine/branchrunner와독립CPUaudit 코드를준비했다. 새합성CPU integration에서benign14/attack16 각5epoch·실10batch/150exposure·원ID/optimizer/RNG/sampler/직렬화가실제통과했다. FU_SOURCE_FREEZE는code-only이고실FU launchprofile/freeze는없다. 실모델/FU/성능재현은미실행이다. 정상FL 실제20R/200roles/2000epoch/40000batch 학습이완료됐으며trainer10000장CA8795/10000=87.95를기록했다. 독립원검증은원controller가아직실행중이므로최종검증통과·STG시작으로미리해석하지않는다. 새readonly normal packet export계약을준비했다. 원독립검증도20R/200role/2000epoch/40000batch·모든집계/optimizer/RNG/원ID와10000장8795정답CA87.95를통과했다. 원foundation은종료했고기존STG parent34020이새trainer49888을한번자동시작했다. 정상검토packet48파일/3payload remoteCPU봉인export가완료됐고local전달/등록은아직이다. 전체STG/공격재현성공은아니다. 정상review양쪽48파일·3payload strictCPU/hash/readonly전달과main23→24/PR20→21/DISLAB21→22 diagnostic case등록·guard/부적격purpose거절이완료됐다. 기존모든case/default/audit를보존했다. full200role는원DISLAB경로보존이며로컬history승인은없다. 원receipt false는역사/최신CLEAN_DELIVERY_COMPLETE가완료근거다. 실제STG trainer49888의surrogate5epoch/3910batch이상을확인했고원normal작업은종료했다. 세모델전체평가/독립전체재추론과순차controller코드를준비하고TF32off/argmax정확일치등을사전선언했다. code-only freeze이며실SSS/FU/평가launch는아직없다. 새23합성평가CPU계약만1회예정이고기존완료검사는반복하지않는다. 새23합성평가CPU계약3개가PR e7cb150 선게시뒤DISLAB에서1회통과했다. 실모델/SSS/FU/평가는미실행이며원계약/실패는불변이다. 미실행독립평가gate를직접정수교차곱으로정적검토한source-only revision2와순차controller가준비됐고실launchprofile은없다. 실SSS query전수치환경을TF32off/matmulhighest/deterministic·실제getter/정책SHA로명시한source-only revision2를준비했다. 기존SSS 수식/선택/허용치·모든완료CPUfreeze와활성STG는불변이며실SSS launch는아직없다. PR5e9a6c5게시뒤원격SSS source-v1을보존하고신source-only/활성STG/완료CPUfreeze해시일치를확인했다. source검토만했으며fixture나실query는반복하지않았다. STG실제100/5/100·78410batch학습이완료돼원parent가독립CPU감사를시작했다. 후속profile 메타데이터준비/일회launch 코드와계약을준비했으며감사통과뒤각profile/freezes를PR에게시하기전실SSS/FU는시작하지않는다. 원STG100/5/100·78410batch학습은완료했지만원독립CPU감사의고정gradient재생maxabs0.009947020560503006이원허용치를넘어실패했다. 205epoch/200step저장·갱신검사뒤실패이며STG_VERIFIED는없다. 원26파일readonly/hash복사와전체raw원위치를보존하고SSS/FU block을유지했다. 별도고정2step/4수치모드·optimizer0회유한진단을준비했고원trainer/전체audit/완료fixture를반복하거나원tolerance를바꾸지않는다. 고정8회수치진단완료: 같은GPU default두gradient는원저장과정확일치0, CPU native/strictGPU 대조도원cross-device기준은미달이었다. 원실패/8회진단은보존하고반복하지않는다. 같은frozen100/5모델·데이터/seed/SGD/기존허용치의새CPU trigger100/200batch 분기복구를선언했으며원GPU branch를덮어쓰지않는다. PRdb35406 선게시/원격freeze검사뒤새CPU복구task를1회시작했다. 실제parent40388/trainer51664·새5epoch10batch이상을확인했고원STG/8회진단은재실행하지않았다. 새CPU감사/SSS/FU/성능은아직미완료다. 새CPU100/200step source·ID/RNG·projection대수와사전두gradient재생maxabs0이통과했다. parent/runner/audit는종료했고원GPU실패는보존했다. 새CPUδ/source binding을미실행SSS/FU/평가에명시연결했으며원STG_VERIFIED를조작하거나완료작업을반복하지않는다. 실SSS/FU/성능은아직없다. 별도CPU binding의metadata prepare를1회실행해정상case guard/원history200role와실4profile·4runfreeze를생성했다. 로컬8sha동일/기존FU·평가수치불변을확인했으며실paired task는publication게시뒤만시작한다. PR22fa9ef 실profile/freezes선게시뒤paired parent31888을1회시작했다. 실제SSS5000장/40batch/80query·125선택(60/65)과독립score/rank/FP64top125·사전두CPUquery가통과했다. 원ID/rank/입력은private보존하고공개counts/hash요약만추가한다. 실benignFU20 runner23964의첫round/client9/2epoch이상진행을확인했으며원SSS/CPU복구/과거finite작업을반복하지않는다. 실제공격FU/동일δ평가/전달/탐지는아직남는다. 실정상FU20 학습완료: 원paired parent31888 아래runner23964가20R/200새역할/1000epoch/20000batch를완료했다. after SHA4027f5a984d99d72572f5972840d03bc3d62877c74f814adb435a31cb792e404·44770315bytes/bare payload를실RESULT로확인했다. 같은parent가새verify_fu.py PID41516을자동1회시작했고17R/170role/850epoch/17000batch까지감사중임을확인했다. 이관측시점최종VERIFIED는아직없어독립감사완료·공격FU완료·성능을미리주장하지않는다. 원runner/audit를다시실행하지않으며감사통과뒤같은parent가공격FU20과후속독립평가를진행한다. D08/D15와공통탐지미검증은그대로다. 실정상FU 독립감사완료: FU_benign_VERIFIED=passed가20R/200role/1000epoch/20000batch·420개history payload해시와전체원ID순회/optimizer/RNG/유효제출출처·보정/집계를검산했다. 원trained23964/verifier41516은실제종료했고같은parent31888이새attack runner19552를자동1회시작했다. 모든localSGD gradient/rawaugmentation 독립재생은아니며실제pre/benign ASR-B/attack성능은아직평가하지않았다. 감사중이던직전summary는당시관측으로보존하고새완료ledger를별도로추가한다. 공격20R·독립감사/동일δ세모델평가·전달/catalogue guards까지전체목표는미완료다. 실공격FU20 학습완료: 원paired parent31888 아래runner19552가20R/200새역할/1000epoch/20000batch를완료했다. after SHA979c789d106a4209d43a7b1cfc0db1cab210508a7367f47e0828afdc9338f0d2·44770315bytes/bare payload를실RESULT로확인했다. 같은parent가verify_fu.py --branch attack PID37328을자동1회시작했고9R/90role/450epoch/9000batch까지감사중임을확인했다. 아직최종VERIFIED·동일δ성능평가는없고정상FU의완료감사/원GPU실패는유지한다. 평가결과를보기전PAIR_DELIVERY_PROTOCOL에대표실기여/optimizer/RNG·전체로그/해시·privateSSS/전수평가자료의양쪽packet범위와원전체raw DISLAB보존·diagnostic등록을명시했다. 전달runner는아직작성/동결/실행하지않았고원paired source는불변이다. 실공격FU 독립CPU감사완료: FU_attack_VERIFIED=passed가20R/200role/1000epoch/20000batch와420개history hash·전체원ID순회/optimizer/RNG·효과제출출처/독립보정·집계를통과했다. 원trainer19552/auditor37328은종료했고같은parent31888이primary evaluate_pair.py PID48424를자동시작했다. 실제최종모델attack의66/79batch·448/474forward까지진행을확인했다. 이시점독립전수평가가아직없어성능판정을미리하지않는다. 모든localSGDgradient/rawaugmentation 독립재생은아니며원GPU STG실패와완료훈련/감사는보존한다. 실paired 최종전수평가완료·성능실패: 두FU 각각20R/200role/1000epoch/20000batch·420hash 독립CPU감사를통과한뒤같은δ·1.5/target2/10000·9000 primary/독립각60000sample-forward를완료했다. 모든argmax/count/logits maxabs0으로정확일치했다. pre CA87.94/ASR6.966666666666667, benign CA86.58/ASR6.322222222222222, attack CA86.76/ASR6.333333333333333으로공격80·전후50pp·정상초과50pp의성능gate는실패했다. 기존정상CA87.95와원GPU STG실패는별도평가역사로보존한다. parent/모든child는종료했으며완료훈련/감사/평가를재실행하지않는다. 최종양쪽review전달·봉인/catalogue/index guards와근거있는후속구현은아직남는다. 최종전달구현준비: 새pair_review_common/export_pair_review/receive_pair_review/register_pair_cases·정확CPUtask launcher와17파일PAIR_REVIEW_FREEZE/실행계약을작성했다. 원실행source/profile/receipt는바꾸지않았다. DISLAB에서신source4개AST·17해시·torch없는hash-onlyguardimport·5경로탈출거절·원20R/양branch대표role metadata·원평가receipt해시의source-only검토가통과했다. tensor읽기/성능추론/완료fixture반복은없다. 새export/전달/등록은이코드와freeze를PR선게시한뒤각새배타경로에서만진행한다. 전달export 첫실행실패보존: PRb6b8dbf source/freeze선게시뒤새CPUtask/PID15136을1회실행했다. 원배타packet928파일/1524947559bytes 복사와첫모델strictCPU/zero1forward뒤진행callback의kind인자중복 TypeError로중단됐다. 원source17freeze/ONCE/publication/trace/events를incident25파일readonly·원바이트로보존했고원prefix928파일의hash/bytes·readonly를봉인했다(SHAbe7f44ce8437db8e2f4253c5db7ae665b2001e530bafa979aeea79530dc45660). 원훈련·평가·모델은불변이고최종CPUreceipt/manifest/archive는없다. 원export를재실행하지않는다. 별도finish복구계약/source/freeze13파일을작성해같은helper를callback없이호출하고원payload재복사없이저장검사/봉인만마무리한다. 원첫zero1검사는uncommitted였으므로새보관검사에서재확인한다. DISLAB의새2파일AST/13해시·prefixmetadata/672pt목록 source-only검토가통과했으며새실제CPU복구는PR선게시뒤만진행한다. privatepacket/zip을양쪽gitignore로명시했다. 양쪽실제pair 전달·등록완료: sourcecallback실패는25파일incident/원928파일prefix로보존하고별도26ba50a CPUfinish가payload재복사없이통과했다. 실제967files/965hash·672typed payload(15model/1delta/656tensor)와전체로그/SSS·평가증거를양쪽readonly로전달했고localstrictCPU/외부archive1,526,179,522bytes SHA6868408d...검사가통과했다. 각host두diagnostic case main24→26/PR21→23/D22→24 append/select_case·부적격purpose거절/모든oldcase/default/audit·UTF8형식보존이통과했다. 전체rawhistory는DISLAB에보존하며local은대표실기여packet이다. 새PAIR_DELIVERY_COMPLETE SHA30e6af46...가실전달완료근거이고원receipt false/parent delivery_pending은역사로불변이다. 성능실패와D08/D15/공통탐지미검증은남아전체목표·heartbeat를끝내지않는다. 새원인진단 사전계약: 저장CPUtrigger의최종CE6.60551와upstream warmup train후eval부재/현재BN-eval고정 차이에근거해새CPU8 mode×zero/finalδ 비교를선언했다. 동일frozen201·마지막저장128/72두batch·800sample-forward/학습0/모델저장0과고정40hit·CE1.0·양batch개선rule/중단규칙이다. DISLAB3AST·6freeze·원source/논문/4payload hash·원연구종료 source-only검사통과(modelLoad/forward0). 실제모델계산은PR선게시뒤1회이며아직미실행이다. BN차이는정상에도가능해D08/D15구별/탐지성공/최종FU유일인과/새학습채택으로승격하지않는다. 새CPU8 진단완료:591e6e4선게시뒤8forward/800sample-forward·학습0/모델저장0을1회완료했다. 모든mode×zero/finalδ의target200정답이0/200이고finalδ CE는eval6.603473/trainBN9.154375여서사전BN-gap rule3조건모두실패/기각이다. 독립저장logit산술검산CE최대5.7687e-7로통과했고모델재추론0이다. parent36844/runner47160/verifier30116은종료/task0이다. PS정책으로원launcher호출이본문전거절된미실행실패와같은바이트새프로세스호출계약5eacb75를보존했고machine정책3은불변이다. 저장원warmup5로그도모든epoch0/200/최종CE9.29416임을새추론없이확인해교사준비부터실패조건이있음을기록했다. 공개concoct_dataset의target+외부인자/원문을근거로새혼합교사후보rationale만작성했으며helperbody누락/정확저자조건미인증/새훈련미실행이다. 원GPU실패·기존FU성능실패·packet/default는불변이고D08/D15/탐지성공은미검증이다. 새단일mixed교사교정구현:공개concoct_dataset의target+외부인자/원warmup0/200에근거해동일fresh201 initial에서Tiny100000+기존target200을100epoch에함께노출하는후보를작성했다. helperbody누락으로저자고유정답인증없다. 기존seed/SGD.1mom.9wd5e-4cos100·warmupRAdam.001/5/B128을유지하고105epoch/78310batch/target21000노출·도메인충돌ID/전체optimizer/RNG·독립CPU105감사·같은저장targetx와Tiny대표의CPU4forward400·독립logit검산을구현했다. 새7syntheticgetitem/2sampler계약만추가하며실자료/모델query0인새검사로기존fixture반복이아니다. DISLAB8AST/PS AST·13freeze·원input/source/caseguard/version/종료 source-only통과(torchimport/modelLoad/forward0). 새fixture/교사훈련/endpoint는PR선게시뒤1회이며아직미실행이다. 모든원실패/전달/default는불변이고최소교사조건은공격/탐지충분조건이아니다. 새교정실시작:860ebd8 source/profile/13freeze선게시와원격검사뒤정확task·parent53016을처음시작했다. 새CPUdomain합성7getitem/2sampler(tail104/72·rawID충돌보존/실자료·모델forward0)이통과했고같은parent가trainer12068을1회시작했다. 실제guard util0/free5045/used5009/disk921674854400 통과/다른앱종료0, ownCUDA이후util32/used6296는시작guard실패가아니다. 실제1mixed epoch100200장/783batch commit·target_seen200과2epoch/700batch이상학습을CIM/STATE/manifest로확인했다. 첫observer의state생성전read-only조회경쟁은생존확인뒤조건조회로구별했고재시작없다. 고정100+5·독립CPU105감사·같은targetx CPU4forward/독립logit검산은진행예정이며아직최종교사/기능개선/공격성공은없다. 원모든완료run/수치/default는불변이다. 활성teacher13source는불변인채별도mixed_trigger source-only를구현했다. core/stg_training/runtime_common3원바이트복사·stdlib completion/binding gate/metadata prepare·미래CPU100 runner/독립audit/controller와15SOURCE_FREEZE다. 코드profile은launchfalse/teacher_bindingnull,실LAUNCH_PROFILE/RUN_FREEZE/task/δ는없다. 새교사105감사·endpoint기존최소조건·실모든종료/task0뒤실bare201 SHA/payload null·정상caseguard를핀하고metadata prepare1회/실profile PR선게시가추가로필요하다. DISLAB10AST/PS AST·15freeze/원helperSHA·기존SGD_CPU4재사용/활성13source불변·닫힌rungate예상거절을통과했다. Torchimport/teacheroutput모델hash/query/새fixture/prepare/새학습0이며실trigger수치검사는아직없다. 원SGD/seed3000/100·200/CPU2/독립2gradient허용치·원모든실패/모델/default를보존하며전체공격/탐지성공으로승격하지않는다. 새mixed교사105epoch/78310batch·독립CPU105감사/동일저장targetx CPU4forward/400sample endpoint·독립저장logit검산이완료됐다. target65/200(기존0)·Tiny훈련대표199/200으로사전약한필요조건은True이며전이/잠복성공은미검증이다. 실제모든teacher종료/task0뒤std-only prepare1회로새bare201 SHA240a2af249a42cd18af4d11513392c94c4c64a279f332e3c27eb17eaf02c8a2f/payload null의실trigger LAUNCH_PROFILE/RUN_FREEZE를준비했다. 원source-only profilefalse/null·모든이전실패는불변이며실profile의PR게시전실trigger는시작하지않는다. 실profile/freeze를f1c925f에계산전게시후정확새CPUtrigger task를1회시작했다. 실제parent13940/trainer55504·13epoch26batch/2600노출commit과동결15원SHA를확인했다. 새100δ/독립감사·새SSS/FU성능은아직없고기존완료작업은재실행하지않았다. 활성mixed CPUtrigger의15source를바꾸지않고별도mixed_pair source-only37freeze/18Python을준비했다. 7helper/기존수치profile·정책은원바이트이며새binding/계산전publication gate와명시original split/history경로만연결했다. 실제prepare/새SSS/FU/evaluation은없고현재trigger독립감사·실종료/task0뒤실profile게시가필요하다. oldSSS/after를새입력으로재사용하지않으며D08/D15미검증은유지한다. 새mixed교사CPUtrigger100/200batch/20000노출·독립300hash/원ID/RNG/200투영(최대1.49e-8)·고정2gradient/augmentation0을통과했고실모든process종료/task0이다. 새δSHA91998234ece2e587cc5435b8d120f113ccfbc1b37d0761e1bf9ad57cf7d42f6b/bare null이며전체200gradient독립재계산은아니다. 새pair source113b3cb/37freeze·18AST/PS·기존fixture SHA재사용/closedgate검토를torch0/modelquery0으로통과했다. 실trigger종료뒤std-only prepare1회·원rawhistory메타데이터20R/200role path검사와새4profile/4freeze가준비됐으며PR게시전실SSS/FU/평가는미실행이다. 기존성능실패/원GPU감사실패/모든case/default는불변이다.  실profile/freeze를a2605a2에선게시한뒤새paired task를1회시작했다. 새SSS5000장/40batch80calls/top125(56/69)와독립전체score/rank·사전2CPUquery검산이완료됐다. score오차2.45e-6/CPUlogit3.43e-5는원허용치내다. sourceIDs/query는private보존하고aggregate/hash만공개했다. 새정상own5/7 N2444/2431·고정local5/B128·원owner7참여9회에따른예상정상batch19955/공격20000이며수치튜닝이아니다. 실제GPUguard통과·parent7756/정상FUtrainer46748를확인했다. 두FU/새성능·최종전달은미완료이고기존모든실패/default는불변이다. 새mixed-pair의read-only상태관측에서Get-Content eventstring의ETS PSDrive/Provider가깊은JSON으로확장되는문제를확인했다. 실제parent/훈련/STATE는정상이고source/model실패·프로세스재시작은없다. 별도운영관측기에서eventJSON파싱/명시필드·50000문자bound를선언하고기존37동결source를바꾸지않았다. 새모델query/학습/fixture는0이며교정관측기사전게시뒤검증한다. 1bea3c0관측기v1의첫probe는embeddedPS선두의불필요한+로본문전에parser실패했다. 원v1/sourcefreeze·trace를보존하고별도v2/explicitPS·새freeze와Python/PS AST검사를준비했다. 로컬구성단계의newline가정assert/미작성파일AST오류도미실행범위를남겼다. 연구source/model/훈련은불변이고v2는새사전게시뒤metadata만관측한다. d735749에선게시한v2 metadata관측은1319문자/50000bound로통과했고실정상FU6Rcommit·7R의CIM/STATE/manifest/event가일치했다. active37source/실runbinding의명시SHA도불변이다. 원v1 parser실패/로컬구성오류·대규모ETS출력의증거는보존하며research/modelquery/fixture/프로세스재시작0이다. 새FU완료나성능성공을뜻하지않는다. 새mixed정상FU가20R/200trained/200calibrated/20global/1000epoch·19955batch를사전동적예상대로완료했다. 새after SHAcd0e6e544a6993e7672e75fff56488141de09d4b12c6e58317cc28bc25793d16이며RESULT SHA1cbe33d2d2f928be222d23b0ef11454e7e94dcb83a064d85b3f17b512aaeb537의원격/로컬바이트를확인했다. 실제parent7756의CPU감사child38220이진행중이고완료학습을감사통과로승격하지않는다. 새공격FU·성능/전달·D08/D15탐지는미완료다. 새정상FU20의독립CPU감사가420historyhash/전체원ID·optimizer/RNG/유효제출출처·독립norm보정/순차집계정확일치로passed다. VERIFIED SHA94f24baee932422b64a0910f581b5fce7f400c130bd4080ab41a54b0dfd1c950의원격/로컬바이트가일치했다. 모든localSGDgradient/rawaugmentation독립재생은아니다. 원AUDIT_STATE auditing은과거이며같은parent7756의새공격process37112가실CIM으로확인됐다. 최초startup STATE부재를재시작근거로쓰지않았다. 공격FU/새성능·전달·D08/D15탐지는미완료다. 후속bounded관측에서같은공격trainer37112의첫R실epoch/STATE/event진행도확인했다. 새공격FU가4R/4000batch를commit한뒤5R/client10의5epoch event 후SSS_RESULT SHA read에서MemoryError로끝났다. 원parent7756/trainer37112/rootPython0/taskexit1이며40committed·5R6개저장trained prefix를보존했다. 사후ownhistorical read-only PowerShell39652의46GB private메모리와정확query/생성시각/parent를확인했으나유일원인은미확정이다. 별도metadata-only ownPS1개종료·streamingprefix보존계약/AST를준비했으며PR선게시전실종료/새훈련은0이다. 정상FU/감사·원source와모든실패를보존하고새수치재개는별도계약이필요하다. 정확ownhistorical PS39652만identity검사후종료해available1.68GB→24.05GB/commit92.05GB→44.43GB를기록했다. 다른앱종료/새훈련0이다. 최초SSH Start-Process prefix보존PID19900은본문ONCE·STATE·실패·결과/출력없이사라져원인미확정으로보존했다. 원source변경없이별도directPython ScheduledTask 호출계약·PS AST를준비했으며선게시전호출은0이다. 동일원보존source의새directScheduled 호출계약을d1aad91/c76932d에선게시뒤처음본문실행했다. 151파일/4R40committed·5R6개저장trained의SHA보존과taskexit0/관련실PID0을확인했고PREFIX_PRESERVED SHAe27f4c6dfd55412bd926230074f897cda432701b67f8d0b62e3930015037d695다. 원모델load/forward/torch/새훈련은0이며이는strictCPU수식감사통과가아니다. 다음새46저장role CPU감사·명시재개계약은닫힌준비이고누락client10 100batch의물리적중복/bit동일성한계를별도기록했다. 원모든실패/완료정상/소스/수치와case/default는불변이다. 새별도mixed_attack_resume의CPU1/-1/forward0 저장prefix46role/230epoch/4600batch·4R독립보정/집계감사source/profile/binding/9freeze를준비했다. DISLAB9sourceSHA/Python3AST/PS2AST는torch/model/fixture0으로통과했고계산전PR게시대기다. 기존완료정상감사·SSS·원finite를반복하지않고GPU재개는닫힌상태다. 원R5참여순서prefix/unsavedclient10의5epoch를구별하며D08/D15탐지성공을뜻하지않는다. 9035d53 CPUprefix 감사v1은PID46388/최초task1회가model load전메모리nestedPowerShell의빈stdout에서JSONDecodeError로종료했다. ONCE/STATE/RESULT0/taskexit1/감사본문torch0이며원source/trace·SHA51f5f92d3abf7f5f9be321c1d34d6987952eb758cf74428acb2854db749b1d60를보존하고재호출하지않는다. 별도nativeMemory guard v2는numerical auditor SHA371db7c8efdfb5d1e2f605a2f43a8a11592e87f0881aa4bed461525246035e36을정확바이트재사용하고metadata 관측만교정했다. DISLAB10SHA/Python4AST/PS2AST/nativeOS getter1회가model0으로통과했고수치감사/새GPU는아직없다. D08/D15는미검증이다. v2 metadata source/실CPUprofile을3e543d1에선게시뒤PID16396의새저장prefix46role/230epoch/4600batch·4R독립보정/집계·전체원ID/optimizer/RNG/BNcounter/inputchain 감사가passed다. 135고유tensorhash/136strictCPU model load·forward/backward/optimizerstep0이며모든SGDgradient/rawaugmentation독립재생은아니다. AUDIT_RESULT SHA301b4b2050fffeefc8d74a58d3b940cb8b8153cd8fd62f008278c8cf2d3e15b0와원격/로컬receipt/실CIM0/taskexit0을확인했다. 원v1guard실패/원MemoryError·모든source/수치는보존했고완료감사를재실행하지않는다. 새GPU복구는별도계약준비이며아직미시작/D08·D15탐지미완료다. 새별도mixed_attack_recovery_run의25sourcefreeze/18Python·3PS AST·원7helper바이트/3수치entrypoint반복문AST동일성검토를모델0으로마쳤다. 원46role를명시참조하고154role/770epoch/15400batch만이어계산하는닫힌source를준비했으며실prepare/GPU/새성능은아직없다. 원실패물리5epoch100batch는유효1000epoch20000batch와구별한다. D08/D15탐지미해결이다. 36037ca source선게시뒤별도stdlib 경로검토와metadata prepare1회를모델0으로완료했다. 실제prepare PID13124/CIM0/Ready/exit0이며원151파일/CPU46·normalcase·자료hash를핀했다. 별도LAUNCH_PROFILE·RUN_FREEZE SHAae54acb74b3c9af7a9346b5468f508268e5a06768d75e0b0ae4227072d714c96·binding을계산전게시하며GPU학습은아직없다. 원실패/닫힌source프로필은불변이다. 실제복구25source를36037ca·실LAUNCH_PROFILE/RUN_FREEZE/binding을18729ce에사전게시한뒤새parent15944/trainer30812가저장46role를원경로로재사용하고새R5client10의5epoch100batch를계산했다. 후속R5/client16/4epoch의STATE/event/CIMparent가일치했고util0/free4380/used5674MiB·RAM가용21.87GB/commit여유43.10GB·경쟁trainer0을통과했다. 원failedtask/완료finite/다른앱종료는0이다. 154role복구학습/fullCPU/새성능·전달은미완료이며D08/D15탐지성공이아니다. 사용자요청으로원문동일PDF의식16–18/TableII/Fig3·4와실평가코드/profile를모델0으로대조했다. ASR비target9000/CA10000·정상FU ASR-B대pre구별은맞지만공식학습50000/각2500 대원문60000/각3000,요청125분모·epsilon좌표/배수·누락helper·단일seed IID조건차이는미인증이다. 논문FedEraser/FedAvg/CIFAR10 CA85.82±.74→85.16±.45와별도최소gate CA80/하락5pp를구별한다. 이전ASR6.33실패를새mixed성능으로쓰지않고새공격은학습중/성능미평가다. 활성source/수치/허용치는변경하지않았다. 새공격복구가20R/유효200role·200calibrated·20global·1000epoch·20000batch를완료했다. 원46재사용/새154실행770epoch15400batch·lost5epoch100batch/물리1005epoch20100batch를구별하며RESULT SHA f62f63662510da96983047fe46b3d0de7dae221d68fb4e35314de41f5e642e7a와원격/로컬bytes가같다. 새after SHA7ada5a25c181e3d5d16d17c97b9de06286d619f3176c0735ccc5c1fa984d86b7/bare null이고trainer30812는끝났다. parent15944의독립전체CPU auditor49744가2R20role까지진행했으며아직감사passed/새ASR·CA/전달은아니다. 원실패·논문조건차이와D08/D15미검증을보존한다. 새공격독립fullCPU20R/200role/1000epoch/20000batch·420hash/전체IDoptimizerRNG·독립보정집계가passed이고VERIFIED SHA c5a9c3f245b12255f2ce1cfbf3b866bb8b7b933db7173fe1678b25a69c2e8705다. 이후primary47628는PAIR_EVAL_ONCE전guard의powershell CreateProcess WinError5로실패해원parent15944도종료/taskexit1/CIM0·평가결과0을보존했다. 학습/감사를재실행하지않는별도evaluation_recovery의24source/14Python·2PS AST·5helper원바이트/원평가수치반복문AST동일성검토를모델0으로마쳤다. 아직native metadata probe/새실profile/GPU평가/ASR·CA는없다. 원실패·D08/D15·논문조건차이는불변이다. 평가native v1의37304 metadata probe는Name/PID/Parent·자신CMD의외부CIM일치를모델0으로통과했으나모든다른Python0 조건은기존10개서비스를경쟁trainer로입증하지못해prepare/실profile/GPU0으로보존했다. 별도native_v2는read-only actual명령줄+원15trainer-token을그대로쓰며32source/14Python·3PS AST/5helper·원두수치반복문동일성을모델0으로확인했다. 아직v2OSprobe/실profile/GPU/ASR·CA는없다. localPowerShell본문전WinError5와별도cmd/file호출·편집syntax오류는미실행범위로보존했고원source/수치/허용치·D08/D15는불변이다. e80b9df선게시 nativev2의S4U Limited metadata probe14524는실13행전체actual명령줄/PID/parent/Name 외부CIM일치·모델0·실종료0을통과했다. 첫stdlib prepare는실pre/정상after/공격after·δ와완료감사를핀했고EVALUATION_INPUT_BINDING c2a1cead/RUN_FREEZE5133dd21의DISLAB·로컬6receipt바이트가같다. 최초hold중DONE조회의부재는prepare0/재실행0인시점역사로보존했다. 실제평가프로필을계산전에게시하며현재새GPU/ASR·CA0이고원수치/32source는불변이다. 새δmixed paired전수평가가완료됐고독립새프로세스와전체입력·argmax/count·logitmaxabs0이일치했다(각60000sample-forward474calls). preCA87.94/ASR29.4666667,정상CA86.77/ASR24.6444444=ASR-B,공격CA86.82/ASR19.3333333이며attack-pre=-10.133333pp/attack-benign=-5.311111pp로억제·활성화4gate실패/CA2gate통과다. RESULT e6904fb0/VERIFIED b01011c9·7receipt바이트/실taskReadyexit0·CIM0/새failure0이근거다. TableII CA85.82±.74→85.16±.45/본문ASR-B약15·최대약89와지표정의·조건차이비교를PAPER_COMPARISON에보존했다. oldδ실패를교체하지않고필요교사인식만으로활성화가보장되지않음을보였다. readonly양쪽전달·새diagnosticcatalogue와전체성능/탐지목표는미완료다. 새mixed_pair_delivery의별도저장가설/대표owner5·7마지막참여규칙·양쪽readonly/typedCPU·host별diagnostic/seal·실패중단계약을모델0설계로작성했다. 아직delivery코드/profile/freeze/task/packet은없고전체성능실패·전달미완료를유지한다. 새mixed전달source13/8Python·1PS/실profile를동결했고첫DISLAB source-only검토가26receipt·대표owner5R20/7R18·SSS40/평가79+237/trigger300 metadata를모델0으로통과했다. 원37/25/32·새13의107sourceSHA와실producer종료를확인했다. source/profile/freezes를전달계산전에게시하며아직export/receive/register/새packet은없다. 이전callback kind실패를새event_type분리로방지하고원보존은불변이다. 5fd1fba선게시새CPUexport가1345files/1343hash/672typed(15model/1δ/656부속) strictCPU·readonly봉인을완료/실taskexit0·CIM0했다. archive1530790988bytes SHA9837cb4f...의로컬전송SHA/bytes도일치했다. localreceiver30540(parent31852)은고정available8GiB를기다리며추출/CPU ONCE/완료0이고등록은아직없다. 대기는실패나중복실행근거가아니다. 같은별도metadata reader/native현재명령으로확인했고다른앱종료/guard우회0이다. 새MONITOR_FREEZE는원13실행source와분리했고main/PR전체privatepacket/zip/partial을ignore했다. 양쪽전달완료를아직주장하지않는다. 2026-11-02 local수신parent31852/receiver30540은native조회에서없고기존session48700도회수불가다. RECEIVE_ONCE/FAILURE/LOCAL_COMPLETE/새packet0이며종료시각·원인·timeout·재부팅은미확정이다. 이미전송검증된archive1530790988bytes와원source13/main·PR각13SHA/별도monitor3SHA·모든원receipt를보존했다. 원격exportReadyexit0/현재process0은유지된다. 기존RAM대기진행기록은역사로남고이번수신소실관측이최신이다. receiver/helper재호출·전송/추출/CPU/등록/완료finite재실행0이고복구는별도명시단계계약·새source/실profile선게시전까지보류한다. 실제local완료전등록/전달완료주장은없으며전체성능·D08/D15/unknowntrigger미검증은불변이다.
2026-11-02 별도 receive-only 복구 계약: 원수신 종료원인 미확정을 보존하고 새ONCE-before-wait/fsync상태/native실제process·terminal을 추가했다. 원13storage수치/검사·source/영수증과CPU1/-1/8GiB/commit16GiB/15초24h는 유지한다. 새5Python/1XML 실profile·freeze·모델0source review·각host 새case/등록부재·remote Ready0/currentprocess0을 PR선게시하며, 이후 새task 단1회만 가능하다. 완료export/scp/훈련/감사/성능평가 재실행0이고 local실제완료 전등록0이다. 성능·D08/D15/unknowntrigger미검증은 불변이다.
2026-11-02 수신복구V1는 source/실profile 선게시후task생성1회가XML인코딩전환불가exit1로실패·task/receiver본문0이며원문·ONCE·failure·terminal을보존했다. 별도monitor import경로오류도metadata본문전모델0으로보존했다. 새별도V2는UTF16LE BOM/선언·monitor경로만교정하고V1실패SHA/부재를추가핀했다. receive_recovery/launcher본문·원13storage함수/17JSON·중단보고/monitor3·고정8GiB/commit16GiB/CPU1/-1/15초24h는같다. 새11source/5Python·1XML·실profile·모델0검사를실행전같은PR선게시하며원/V1helper·receiver재호출과완료export/scp/훈련/감사/평가재실행0이다. actuallocal완료전등록0/전체성능·D08/D15·unknowntrigger미검증은불변이다.
2026-11-02 V2 UTF16 task생성0/query0후기본RunLevel필드생략검증실패를보존했다. task는미실행Ready3/267011이고수신본문·ONCE0이다. 별도start-only 모델0검사는실COM RunLevel0/state3/neverrun267011·실등록XMLcanonicalSHA를확인했다. 새4Python/1readonlyJScript·실profile/freeze를선게시한뒤기존task첫/Run만1회요청하며task재생성/수정/원V1V2launcher재호출0이다. 수신본문·원13storage/원archive·영수증·8GiB/commit16GiB/CPU1/-1/24h는불변이고완료계산재실행0·actuallocal완료전등록0·성능/D08/D15/unknowntrigger미검증은유지한다.
2026-11-02 8b007fa start-only 실source/profile 선게시후이미등록된미실행V2task첫/Run1회exit0. 실제native PID30052/parent3508 exactcommand와COM RunLevel0/Running4/267009·대기전ONCE·실process·24hdeadline/fsync상태·최소2개15초guard sample이일치했다. 원/V1/V2launcher재호출·task재생성/수정0이다. 가용8GiB/commit16GiB 대기이며추출/672localCPU/완료/등록0·완료export/scp/훈련/감사/성능평가재실행0이다. 실제PID는시점관측이며반복metadata는새observe_start.py를쓴다. 원소실원인미확정과V1 XML/V2기본필드검증실패·모든sourcefreeze/성능실패/D08/D15/unknowntrigger미검증을보존한다.
2026-11-02 새receiver30052는04:35 실제native0/taskReady3/result0x40010004이며마지막04:28:21 sample46/690.766초·47fsyncguardprefix를보존했다. 같은시간대System종료/새시작기록과새OSuptime을확인했고TaskScheduler history는disabled/own이력0이었다. 개별process종료주체·기제·RAM원인·24h timeout은입증하지않으며원Nov1소실원인으로소급하지않는다. 새extract/CPU/producerfailure·terminal/localpacket/완료/등록0·receiver/taskRun/완료계산재실행0이다. 원source13/V1 10/V2 11/start8·원archive/영수증·catalogue바이트는보존했다. 다음수신은fixed8GiB/commit16GiB충족과새명시단계계약/source실profile선게시뒤에만가능하며그전새장기대기receiver/자동재시작은없다. 전체성능/D08/D15/unknowntrigger미검증을유지한다.
2026-11-02 사용자원인질문후읽기전용STG source/저장로그검토: 고정공식fullraw8763bytes/Gitblobbb5096db/SHA53e77435를확인하고실15source·entrymain→projected_sgd_batch→core.trigger_step AST를결속했다. 원RAdam+Cosine/trigger전eval없음/latentforwardclamp 대실SGDfixedLR/evalBN/step후투영의이미선언된차이가있다. 교사무교란endpoint65/200·CE2.5103과달리기존augmentedtrigger훈련manifest최종CE.431044/최소99epoch.401918도같이보존했다. 서로다른입력이므로통제된효과/정답수/ASR로환산하지않고전이·BEA활성화실패의단일인과원인은미확정이다. 원BN CPU8기각을보존하며RAdam/BN교정채택·새학습/추론/gradient/완료계산재실행0이다. localRAM/재시작문제와성능실패를분리하고D08/D15/unknowntrigger미검증은유지한다. 새사용자DISLAB우선지시에따라로컬전달을선행조건으로두지않고공식STG AST174..216/limit_noise를직접사용한별도패키지비교를선언했다. 8c37972 actualsource/profile 선게시·역포트AST정확일치/8AST·원입력SHA/model0검사뒤detached본문0소실을보존하고f86f905 foreground연결복구만추가했다. 같은mixed105교사와saved200입력/CPU2를고정한RAdam+cos/trainBN/latent-forwardclamp 새비교가실parent26988→27516/ONCE/STATE로진행중이며완료훈련·SSS·FU·평가재실행0이다. 최대100/원zero-gradientbreak·새optimizer/2gradient감사·동일원교사zero/old/newδ6forward후멈추고새SSS/FU는별도명시계약전자동시작0이다. 개별변경인과/공격성공/탐지성공은미확정이며D08/D15반례는유지한다. 새공식STG패키지DISLAB100epoch/200step와독립200RAdam상태·첫/마지막2gradient maxabs0/저장logit산술검사가완료됐다. 동일원교사·동일200입력에서zero65/200 CE2.5103,기존SGDδ184/200 CE.342512,새패키지δ0/200 CE9.55301로RAdam/BN경로를맞추면해결된다는가설은지지되지않았고새δ를채택하지않았다. 원함수의숫자와최종피해ASR실패는별개이며개별변경인과는미분리다. 기존δ가교사에서학습됐다는새직접관측에근거해고정외부2000장의class별선택성과같은δ×1.5의교사/피해모델전이를64forward/8000표본·학습0으로확인하는별도진단source/profile을준비했다. 전수외부class2의200장은교사훈련자료이며다른1800ID와분리해보고하고표준10000/9000ASR·FU재현으로대체하지않는다. 사전정수selectivity/transfer조건·중단규칙과D08/D15미해결을유지한다. 사전b15eff7의새고정외부2000 semantic/transfer진단64calls/8000sample-forward가DISLAB에서완료됐고모든weight/BN은불변·학습0이다. 교사zero는targetclass74/200·비target1/1800,기존δ×1.5에서비target1290/1800이었다. 같은입력피해모델비targettarget예측은46→588/1800으로부분전이가있었고사전selectivity/transfer정수조건둘다통과했다. 모델0독립저장logit전수argmax/count/교차표와NumPy재구성64inputSHA가정확일치했고양process종료/exit0/failure0이다. 따라서교사학습·전이가전혀없었다는설명은배제하지만전이강도/SSS·BEA·FU중최종원인은미분리이며새표준ASR/FU재현이아니다. metadata prettyJSON출력잘림은별도보존하고수치재실행0이다. 두새한정프로토콜은종료했고원실패/큰정상반례/unknowntrigger미검증/전체목표미완료는유지한다. 새target-only125 교정: 기존125에는targetclass2가0개였고공개feature분기 제한의새125는전부class2(owner58/67)다. source/실profile선게시뒤원호출정책·전달·quoting오류를본문0으로보존했다. 첫target-only task는실profile 저장형식키누락으로첫모델초기화/epoch전에종료(.pt0/δCPU읽기만)했다. 원source/failure/Readyexit1은불변이다. 별도a87ccb2 source/099a095 actualprofile 복구는원globalnull/rolemodel키만회복·AST필수FU키검사passed 후같은125선택/δ/전체조건으로DISLAB parent33084→trainer41032 실제학습을시작했다. 정상20R/공격20R·독립CPU·전수primary/독립평가·readonlyreview가동일parent순차이며현재첫round의실trained역할저장을확인했다. 최종CA/ASR/성공은아직없다. 전체목표/탐지미검증은그대로다. 새targetclass-only125 정상FU20이20R/200role/1000epoch/20000batch를실제완료했다. afterSHA8b44c116d8d5fff963f37ffeeeedcef31623cc98a182e91f6bf39e8e5a48a035/bare44770315bytes를실RESULT로확인했고trainer41032는종료했다. 같은parent33084→새CPUauditor52780의실제명령줄/STATE를확인했으며이관측시점감사최종통과·공격완료·CA/ASR성공은주장하지않는다. metadata수집model0·원훈련/감사재실행0이며원source/실패/반례를보존한다. 새target-only125 정상FU20 독립CPU감사가20R/200role/1000epoch/20000batch·420historyhash와전체ID순열/optimizer/RNG·유효보정/집계정확일치를통과했다. after8b44c116...는RESULT와같고모든localSGDgradient재생은아니다. 원trainer41032/auditor52780종료뒤같은parent33084가실공격trainer46984를1회자동시작했으며공격3Rcommit/4R학습을실명령줄/STATE로확인했다. 새최종CA/ASR·공격완료·성공은미측정이고원계산재실행0/반례보존이다. 새target-only125 공격FU20도20R/200role/1000epoch/20000batch를실제완료했다. after74a89cab181896bce275a271d373db40d55fad9b4942261b75f441bea5b4e182/44770315bytes/bare를실RESULT로확인했고trainer46984는종료했다. 같은parent33084→새CPUauditor14808의실명령줄/STATE를확인했다. 이관측시점최종공격감사/표준CA·ASR/성공은아직주장하지않으며정상완료감사와모든원실패/반례를보존한다. metadata수집model0/완료계산재실행0이다. 새target-only125도양FU20/각420hashCPU감사·primary/독립각60000sample474calls/모든raw입력·argmax·count정확일치/logitmaxabs0을완료했다. 새pre CA87.94/ASR29.466666666666665,정상86.58/ASR-B22.288888888888888,공격86.88/ASR26.155555555555555로원4성능gate실패/2CA통과다. target-only선택만으로복구되지않았고정확유일실패인과는미분리다. 원parent33084/모든child종료·taskReadyexit0/process0/failure0이며실pre/정상8b44c116.../공격74a89cab...·전체raw400role/로그를DISLAB에보존했다. 새원격459hash/365typedreadonlyreview·677129078bytesarchive봉인완료이고local전달/새case등록은별도미완료다. 완료훈련/평가/감사/export재실행0/전체목표미완료/기존반례는불변이다. 성능실패뒤읽기전용source/원historyJSON대조에서공개main의고정selected10/owner5·7매round참여대현재random10/20의기존선언차이를정량화했다. 선택125의현재예제epoch노출5045 대동일125의fixed20R12500,현재첫roundowner둘부재를확인했다. 고정cohort새foundation/FU는새source/실profile선게시전미실행후보이며유일인과/성공보장은아니다. 모델load/forward/gradient0으로BEAhelper누락의augmentation순서를새로추정해채택하지않았다. 공개fixed10조건의새별도foundation source892025f/actual4152be6 선게시·12AST/selector외수치AST정확·원initializer/split/공식자료SHA·public23Git바이트일치검사뒤DISLAB parent14064→trainer13216으로실제fresh20R학습을시작했다. 고정selected[2,3,5,7,9,12,13,16,18,19]·owner5/7매round이며초기모델/분할seed42·원SGD/epoch/수치반복문은유지했다. 현재실epoch진행만확인했고최종pre/CA·새SSS/FU/성공은미완료다. 새pre·SSS도바뀌므로노출만의유일인과실험으로부르지않고실패/반례/원scope는보존한다. 새fixed10정상보관·등록source만1a9fb57선게시해DISLAB12AST/5helper·원freeze/새case없음검토를model0으로통과했다. 3strictCPU/봉인/export/등록은미실행이며foundation종료+actualprofile선게시뒤만진행한다. 학습은실5Rcommit/6R진행·실process일치/failure0이고후속새SSS/pairedFU가남는다. 새fixed10피해모델에대한새SSS5000/80query·targetclass2-only정확global125 source를cf01f5f에선게시했다. DISLAB16AST/11unchangedfile·querybackend/CPU2replay ASTexact를model0검토했으며실prepare/query/task0이다. 새pre봉인/등록·실profile게시뒤만시작하고SSS뒤별도pairedFU/전수성능이필요하다. 새fixed10/newSSS pairedFU20 source를00cc926에선게시해DISLAB21AST/18기존filebytes·FU필수7키(globalnull/rolemodel)·원6gate불변을model0검토했다. Foundation11Rcommit/12R실진행/failure0이며새paired actualprepare/훈련은아직0이다. 새foundation/봉인case/SSS완료·실입력/선택/profile선게시뒤만후속1회진행한다. 새fixed10 clean20R/200roles2000epoch40000batch·독립220historyhash/10000CA8552정답85.52가완료됐다. 원taskReadyexit0/native0/failure0이며새preSHAa4cd527f...를보존하고별도normal보관첫stdlibprepare(model0)로actual입력/profile/freezes를생성했다. 실제SSS/paired성능은아직미측정이며actualprofile게시뒤만CPUexport/새case와후속SSS/FU를진행한다. 새fixed10정상packet73file/71hash/3CPUzero1·봉인/ZIP와DISLABdiagnosticcase24→25등록이완료됐다. 기존15auditbytes/default/cases와main/PRcatalogue는보존했다. remote등록후localcp949readback오류는기존UTF8영수증만읽는명시metadata복구로검산하고등록·모델반복0을유지했다. 새SSS첫stdlibprepare도새pre/guard/actualprofile·freeze를생성했으며게시뒤80query첫1회만진행한다. 새fixed10SSS5000/80query·targetonly125(owner63/62)와전체score/rank/FP64선택집합·고정CPU2batch검사가완료됐다. 고정first128+last68의4call실392sample-forward인데계획400표기가잘못됐음을원profile/source/결과불변의별도metadata정정계약으로보존했다. 원400계약통과는주장하지않고추가추론·재실행0/수치·선택·예산불변으로392범위만후속paired에결속한다. fixed10신paired첫stdlibprepare는실upstream3taskReadyexit0/native0/새caseguard·pre/SSS SHA와필수payload키를핀하고normal/attack각20000batch·각20R1000epoch/선택12500노출을학습전에계산했다. count정정binding/실FU·EVAL·LAUNCHprofile/3freeze를별도게시한뒤만첫pairedtask를시작하며privateSSS/IDs는공개하지않는다. 3474a34의실profile선게시/51publicbytes일치·private3입력SHA·392count정정결속뒤새pairedparent32316→normaltrainer17820이1회시작해1Rcommit/2R실epoch를진행했다. 긴metadataobserver전달실패는source·trace보존/별도compactV2조회model0으로복구했고실훈련오류·재시작0이다. 최종CA/ASR는아직미측정이며동일부모의정상/CPU/공격/CPU/독립전수/readonlyreview를계속한다. fixed10정상FU20도실20R/200roles1000epoch20000batch·afterSHA85030dfc.../44770315bare로학습완료했다. 원trainer17820종료/parent32316→새CPUauditor29824를실확인했고17:32관측감사중/failure0이다. 원모델·source불변,collector모델0이며최종VERIFIED/공격·CA-ASR완료를미리주장하지않는다. fixed10정상FU20 독립CPU감사도20R/200trained200calibrated·1000epoch20000batch/420historyhash·전체ID/RNG/optimizer/유효보정·집계를통과했다(VERIFIEDf74afc84...). 원trainer17820/auditor29824종료뒤같은parent32316→새attack22700이자동1회시작해1R실epoch를확인했다. 공격·최종CA/ASR는미완료이며원AUDIT_STATE auditing20을live근거로쓰지않는다. 최신fixed10/newSSS pairedFU20도실완료했으나성능실패다. preCA85.53/ASR20.144444444444446,정상CA84.74/ASR-B16.666666666666668,공격CA84.69/ASR13.822222222222223로공격-pre -6.322222222222222pp/정상초과 -2.8444444444444446pp,4성능gate실패/2CA통과다. 양FU각20R/200trained200calibrated/1000epoch20000batch/420historyhashCPU통과,모든SGDgradient재생아님. primary/독립각60000/474·raw입력/argmax/count정확/logit0. 실제공격after3deabcbe...와523hash365typedreadonly원격packet·archive677289556bytesSHA0979db17...보존,정확taskReadyexit0/native0/failure0. foundation85.52와paired85.53한장차이는평가route차이관측으로보존/원인미분리/재추론0. 원SSS400미충족·실392정정/모든과거실패/source/default/case불변. 고정owner매round노출로도활성화가복구되지않았으며새pre/SSS동시변경으로단일원인미분리다. local전달/탐지/전체성능목표미완료이며추가모델실험은새근거·별도사전계약전보류한다. fixed10완료실패뒤같은publisher계정의별도FedUBA-2@9e65a5cd가동일root9blob과별도FedUBA.zip을게시한것을찾아누락helper회복가능성의모델0 ZIP/AST읽기전용검토를사전게시했다. 새모델실험/수치변경은없고아직ZIP본문결과는미확인이다. 새대안ZIP의첫모델0검토가AST NULbytes에서실패해원source/REVIEW_FAILURE/ONCE/실ZIP을보존했다. member원인은아직미확정이고원inspector재호출없이AppleDouble 경로와magic이함께맞을때만메타데이터로분리하는새명시stdlib 복구계약을선게시했다. 실제Python본문검사완화/다운로드재시도/모델실행0이다. 대안저자계정ZIP검토완료: 실제21member/8Python+README9본문이기존root9blob과모두같고누락helper/models정의0이다. 원NUL실패는AppleDouble경로+00051607가함께맞는8resource metadata로분리한새명시복구에서원다운로드재사용/모델0으로완료했으며원실패/소스불변이다. 이출처후보는종료하고새helper획득이나성능원인인증으로승격하지않는다. 새원격보고서2개송신뒤local metadata finalizer가slash정규식오류로실패한것은원producer완료와분리보존했다. 별도String.Replace읽기전용계약으로기존4metadataSHA/원rootprocess0를검산했고producer/mirror/ZIP/AST재실행0이다. 新fixed10SSS 저장40query의logit방향을선택target125/비선택target343/비target4532로고정대조하는별도CPU artifact진단source/실profile를선게시했다. 모델state/교사/delta load·forward·SSS재query0,과반margin감소조건은사전정수고정이며새선택/전체재훈련채택을허용하지않는다. 현재packet계산결과는미측정이다. 新fixed10SSS 저장logit방향진단완료:선택target125중76margin감소/49증가(target118→96),비선택target343은202감소/141증가(332→315),비target4532는3858증가/674감소(target22→334). 사전과반조건은충족했으나비선택target도비슷해selector고유원인/새selector채택/전체재훈련근거로승격하지않는다. 기존40packet만DISLAB CPU역직렬화/모델load·forward0,독립torch없는5000행argmax·margin부호집계/FP64평균CE오차3.55e-15통과,원PT독립재열람아님. foregroundexit0/parent37592·모든child종료/native0/failure0. SSS x+delta/noClip/배수1·학습자료진단이며표준ASR나실BEA negative/clip으로대체하지않는다. 원모든source/모델/SSS392정정/선택/default/실패불변,후속은원문Eq8/실request연결증거대조뒤별도고정계약으로만한다. 관련 helper의 동일 poison_image 호출 signature/positive addition 대 논문 Eq8 negative 부호 차이를 새 source-only 조건으로 분리했다. 정상/minus baseline·새SSS선택은 원위치 명시재사용, 변경은 selected-image sign 한 개이며 helper의 추가 dataset getitem/RNG는 미채택. synthetic4 CPU 계약·새 attackFU20/CPU·후속 새 모델만 평가 계획을 선게시하며 아직 신규실행/성능0, Eq8적합/누락helper복구/탐지성공 미주장. 새 related-helper positive 부호 조건을5e50bf6에先게시뒤DISLAB source18AST/17기존bytes/숫자한literal·FU7키/원6gate검토와synthetic4 exact CPU계약을1회통과했다(model/realdata/forward0,CUDA미초기화;원helper8/new4 getitem범위명시). 네완료taskReady0/native0와같은pre/SSS125 owner63/62/기존정상minusbaseline을metadata결속해새공격만FU20/20000batch/12500exposure actualprofile/freezes준비완료,실학습/성능아직0. 새actual metadata선게시 guard는원DISLAB CRLF JSON 대 Git자동정규화byte불일치에서commit/훈련전에중단했다. 원receipt/source/freeze와caller/assert를보존하고새폴더 .gitattributes -text 및별도metadata packaging계약으로원rawbytes만게시할명시복구를진행한다. 생산자/CPU/prepare재실행없다. 새positive-sign FU20을50951df actualprofile선게시후유일task parent8788→trainer38692로시작,04:33:39Z4Rcommit/5R실학습·실command/parent/LimitedtaskRunning/failure0. 정상minus/SSS재실행없이sourcefreeze1691ff30/runfreeze1eefd2e2불변. 새attack만각20000sample158calls평가·새3modelCPU/readonly보관의별도source를학습중준비했고actualprepare는새FU20/CPU종료뒤만가능하다. 최종성능/성공은미측정이다. 별도평가source d8ca176/freeze031d84db의DISLAB17AST/PSAST/11helperbytes·primary/independent수치loop AST·원6gate정수산술 model0검토통과. 기존pre/benign재추론0·새attack각20000/158·새3modelCPU보관범위를선언했고actualprepare/모델읽기/평가/task0이다. 새positive-sign attackFU20/독립CPU실완료:after1910705b.../44770315bare null,RESULTd6d77e03.../VERIFIEDb0c2ec99.../COMPLETION36a54ccf...,20R200trained200calibrated1000epoch20000batch/420hash·전체ID순열/optimizerRNG/유효첫round출처·독립보정집계BN통과,모든gradient/augmentation재생아님. 정확taskReady0/native0/failure0이며구AUDIT_STATE는역사다. 후속새attack-only평가actualprepare를1회완료해새after/원pre정상증거·봉인을결속했고각20000/158·원6gate·새3model CPU보관profile를선게시,아직새최종성능0이다. 첫평가localcaller를publication-pin process종료확인전에호출한순서오류로RUN_PUBLICATION읽기에서중단했다. LOCAL_LAUNCH_ONCE/SSH/PS/task/모델실행전실패·task없음/native0를보존했고원caller재호출0. pin은그뒤43publicbytes일치/344b7af actual게시로완료됐다. 새명시transport-only계약/source/profile/freezes를선게시해같은불변PS를처음1회호출하며수치/예산/권한/원source/profile변경없다. positive primaryCA84.45/ASR58.74444444444445(5287/9000),원6gate4성능실패2CA통과. 실제primary18780·독립57372각20000/158/마지막79batchmaxlogit0뒤확인서dictline147의inputs변수shadow KeyError로독립taskexit1/원VERIFIED·COMPLETION부재·export0. 원source/trace/결과/Readyexit1/native0보존. 새별도prefix-review/3신모델CPU보관source·실PROFILE를선게시해기존control-flow/STATE/정수결과를한정검토하며원검증성공/원VERIFIED합성/재추론0;새3zero1보관만예정이다. 새9007769 prefix/storage계약을실행해고정source/control-flow·trace/STATE로158call완료비교prefix를한정확인했으나원verifier성공/원VERIFIED합성0. 새3modelstrictCPU/finite/zero1×3·286hash161typed readonlyarchive357362282bytesSHA7bdc28ac.../manifest629c2464.../seal89cc325c...완료,새foregroundexit0/native0/failure0와원평가Readyexit1/원VERIFIED부재를함께보존했다. primaryplusCA84.45/ASR58.7444는minus13.8222보다44.9222pp높지만원4성능gate실패2CA통과/저자helper·식8정확재현·탐지성공아님. 모든실모델job종료,local전달/등록과전체목표미완료;새관측없는전체재훈련보류. 새model-free RNG경계source검토를준비했다. 공개import/seed/cache/constructor순서·explicitgenerator keyword와실명시role-seed정수schedule을AST로결속하며upstream/torch/RNG/model실행0이다. 역할별seed정책은이미선언됐고minus/plus공통helper라양부호성능차이원인/seed튜닝·새wholetraining근거로채택하지않는다. missingimports로원저자stream실행인증도아니다. 440b0b8선게시뒤model0/RNG0/torchimport0의DISLAB readonly RNG-source검토완료. public4seed호출(module0세개/mainTorch42한개)/13DataLoader explicitgenerator0/두model_init호출이cache조건보다앞임을AST로확인했지만missingimports때문에untouched실행인증아니다. actualrole-reset+별도generator/정수200seed는이미선언된정책이며minus/plus3helperhash동일로seed변경·성능gap원인·재훈련채택0. furthercorrection미검증보류·원ASR58.7444/4성능gate실패/원확인서오류불변. Localnativeavailable4.706GiB/commitfree28.079로8GiBguard미달·새receiver/waiter0이다.
2026-11-03 사용자 DISLAB 즉시계속 지시에 따라 확인된 독립평가 확인서 변수shadow 오류의 별도 운영복구를 선게시한다. 원실패/taskexit1/원VERIFIED부재·봉인은 그대로 두고 새root에서metadata binding명과출력경계만교정해동일attack20000sample/158call 독립검증을추가1회한다. 수치main AST전체일치/원6gate와허용치/모델1910705b...·delta·pre정상재사용을고정하며학습/primary/oldverifier/export재실행0,성능교정이나탐지성공아니다. DISLAB가용RAM약17GiB/GPUfree5045MiB여서정리삭제가필요하지않았고localRAM을진입조건으로두지않는다. 실제검증은source/실profile게시·새source-only검토·actualrun결속뒤만실행한다.
새독립운영복구 source a16bed4 선게시뒤DISLAB stdlib6AST·main전체AST(metadata binding/ONCE경계만정규화)정확과13actual/GitHub bytes가통과했다. 원두task Ready/exit0·exit1/native0·실패를보존한actualrunfreeze를게시하며모델/query0이다. 실제추가독립평가는게시commit핀뒤동일20000/158만1회한다.
사용자 DISLAB즉시실행 지시에따라 새독립 writer복구를실완료했다. source a16bed4/actual5e75844 先게시뒤새foreground/GPUchild각1회 동일after1910705b.../delta로20000sample158call·raw10000입력/argmax/count정확/logitmaxabs0을통과했고RECOVERY_VERIFIED6294fcac.../별도COMPLETION이생성됐다. 새stageexit0/native0/failure0인2026-11-03T11:14:56Z와원taskexit1·원VERIFIED/COMPLETION부재/모든원실패bytes를함께보존한다. pre정상수치는기존같은route명시SHA재사용/재추론0이며훈련/SSS/primary/oldverifier/CPUarchive/export반복0이다. plusCA84.45/ASR58.74444444444445(5287/9000)·4성능실패2CA통과는그대로이며새확인서복구가성능향상이나탐지성공은아니다. DISLAB가용RAM17.146GiB/commitfree42.646GiB/GPUutil0free5045used5009/competitor0/disk조건통과로삭제0이며localRAM은DISLAB선행조건이아니다. 새보고서와14metadata DISLAB/local SHA동일로보존했고기존packet/seal/catalogue/default는불변,local전달/전체목표는미완료다.
미검토 관련Narcissus concoct_dataset의2인수constructor 대 FedUBA3인수(CIFARflag) 호출을 새model-free 의존성호환성후보로분리했다. 고정원source3개/profile만읽는stdlib AST와5합성위치/최대8wrappedgetitem으로directdropin필요조건·concat/label/getitem경계를계산전선게시한다. 실제저자누락helper회복/교사RNG인과·새훈련채택은주장하지않고thirdflag를임의해석하지않는다. 모델/tensor/RNG/forward0 계약이며기존교사·STG·SSS/FU/평가는반복하지않는다.
- **non-IID에 대해 남길 교훈:** 적격 공격 양성 확보 전 탐지를 검증할 수 없고, 재현 통과 자체도 D08 공격0.75848/정상0.75525·0.76188 및 D15 반례를 해결하지 않는다.
- **반복하지 않을 주장:** 누락 utils/models를 추측해 넣고 untouched 논문 재현이라고 부르거나 stcebra/FUBA 실패 모델을 FedUBA로 대체하지 않는다. 완료된 감사 runner와 이전 FUBA 유한 작업을 자동 반복하지 않는다.
- **재검토 조건:** 권위 있는 누락 정의·데이터/ID/BEA 의미 및 설정 차이를 해소한 별도 고정 profile, 실제 동일 FU 정상 대조, 독립 정상 보정과 새로운 행동 가설을 먼저 확보한다.

**원문·증거:**

- [research/feduba_reproduction_audit_20261031/PROTOCOL.txt](feduba_reproduction_audit_20261031/PROTOCOL.txt)
- [research/feduba_reproduction_audit_20261031/FREEZE.json](feduba_reproduction_audit_20261031/FREEZE.json)
- [research/feduba_reproduction_audit_20261031/CODE_PAPER_MATRIX.txt](feduba_reproduction_audit_20261031/CODE_PAPER_MATRIX.txt)
- [research/feduba_reproduction_audit_20261031/DETECTION_GATES.txt](feduba_reproduction_audit_20261031/DETECTION_GATES.txt)
- [research/feduba_reproduction_audit_20261031/REPORT_KO.txt](feduba_reproduction_audit_20261031/REPORT_KO.txt)
- [research/feduba_reproduction_audit_20261031/RESULTS.json](feduba_reproduction_audit_20261031/RESULTS.json)
- [research/feduba_reproduction_audit_20261031/ASSET_SUMMARY.json](feduba_reproduction_audit_20261031/ASSET_SUMMARY.json)
- [research/feduba_reproduction_audit_20261031/DISLAB_VERIFICATION.json](feduba_reproduction_audit_20261031/DISLAB_VERIFICATION.json)
- [research/feduba_reproduction_audit_20261031/DISLAB_AMENDMENT.txt](feduba_reproduction_audit_20261031/DISLAB_AMENDMENT.txt)
- [research/feduba_reproduction_audit_20261031/PUBLICATION_MANIFEST.json](feduba_reproduction_audit_20261031/PUBLICATION_MANIFEST.json)
- [research/feduba_paper_implementation_20261031/RETARGET_PROTOCOL.txt](feduba_paper_implementation_20261031/RETARGET_PROTOCOL.txt)
- [research/feduba_paper_implementation_20261031/PREVIOUS_QUEUE_STOPPED.json](feduba_paper_implementation_20261031/PREVIOUS_QUEUE_STOPPED.json)
- [research/feduba_paper_implementation_20261031/SOURCE_PROVENANCE.json](feduba_paper_implementation_20261031/SOURCE_PROVENANCE.json)
- [research/feduba_paper_implementation_20261031/CORE_CONTRACT.txt](feduba_paper_implementation_20261031/CORE_CONTRACT.txt)
- [research/feduba_paper_implementation_20261031/CORE_FREEZE.json](feduba_paper_implementation_20261031/CORE_FREEZE.json)
- [research/feduba_paper_implementation_20261031/CORE_CPU_RESULT.json](feduba_paper_implementation_20261031/CORE_CPU_RESULT.json)
- [research/feduba_paper_implementation_20261031/REPORT_KO.txt](feduba_paper_implementation_20261031/REPORT_KO.txt)
- [research/feduba_paper_implementation_20261031/GPU_PREFLIGHT_PROTOCOL.txt](feduba_paper_implementation_20261031/GPU_PREFLIGHT_PROTOCOL.txt)
- [research/feduba_paper_implementation_20261031/GPU_PREFLIGHT_FREEZE.json](feduba_paper_implementation_20261031/GPU_PREFLIGHT_FREEZE.json)
- [research/feduba_paper_implementation_20261031/CLEAN_FL_PROTOCOL.txt](feduba_paper_implementation_20261031/CLEAN_FL_PROTOCOL.txt)
- [research/feduba_paper_implementation_20261031/CLEAN_FL_PROFILE.json](feduba_paper_implementation_20261031/CLEAN_FL_PROFILE.json)
- [research/feduba_paper_implementation_20261031/CLEAN_FL_FREEZE.json](feduba_paper_implementation_20261031/CLEAN_FL_FREEZE.json)
- [research/feduba_paper_implementation_20261031/FOUNDATION_FREEZE.json](feduba_paper_implementation_20261031/FOUNDATION_FREEZE.json)
- [research/feduba_paper_implementation_20261031/MONITOR_PROTOCOL.txt](feduba_paper_implementation_20261031/MONITOR_PROTOCOL.txt)
- [research/feduba_paper_implementation_20261031/GPU_PREFLIGHT_RESULT.json](feduba_paper_implementation_20261031/GPU_PREFLIGHT_RESULT.json)
- [research/feduba_paper_implementation_20261031/CLEAN_FL_READY.json](feduba_paper_implementation_20261031/CLEAN_FL_READY.json)
- [research/feduba_paper_implementation_20261031/FOUNDATION_ONCE.json](feduba_paper_implementation_20261031/FOUNDATION_ONCE.json)
- [research/feduba_paper_implementation_20261031/CLEAN_FL_STARTED.json](feduba_paper_implementation_20261031/CLEAN_FL_STARTED.json)
- [research/feduba_paper_implementation_20261031/ASSET_PROTOCOL.txt](feduba_paper_implementation_20261031/ASSET_PROTOCOL.txt)
- [research/feduba_paper_implementation_20261031/ASSET_PROFILE.json](feduba_paper_implementation_20261031/ASSET_PROFILE.json)
- [research/feduba_paper_implementation_20261031/ASSET_FREEZE.json](feduba_paper_implementation_20261031/ASSET_FREEZE.json)
- [research/feduba_paper_implementation_20261031/EXTERNAL_SOURCE_METADATA.json](feduba_paper_implementation_20261031/EXTERNAL_SOURCE_METADATA.json)
- [research/feduba_paper_implementation_20261031/ASSET_FAILURE.json](feduba_paper_implementation_20261031/ASSET_FAILURE.json)
- [research/feduba_paper_implementation_20261031/ASSET_CPU_RECOVERY_PROTOCOL.txt](feduba_paper_implementation_20261031/ASSET_CPU_RECOVERY_PROTOCOL.txt)
- [research/feduba_paper_implementation_20261031/ASSET_CPU2_FREEZE.json](feduba_paper_implementation_20261031/ASSET_CPU2_FREEZE.json)
- [research/feduba_paper_implementation_20261031/incidents/asset_cpu_visibility_v1/MANIFEST.json](feduba_paper_implementation_20261031/incidents/asset_cpu_visibility_v1/MANIFEST.json)
- [research/feduba_paper_implementation_20261031/CPU_VISIBILITY_DIAGNOSIS.json](feduba_paper_implementation_20261031/CPU_VISIBILITY_DIAGNOSIS.json)
- [research/feduba_paper_implementation_20261031/STG_PROTOCOL.txt](feduba_paper_implementation_20261031/STG_PROTOCOL.txt)
- [research/feduba_paper_implementation_20261031/STG_PROFILE.json](feduba_paper_implementation_20261031/STG_PROFILE.json)
- [research/feduba_paper_implementation_20261031/STG_SGD_CPU_FREEZE.json](feduba_paper_implementation_20261031/STG_SGD_CPU_FREEZE.json)
- [research/feduba_paper_implementation_20261031/ASSET_CPU2_RESULT.json](feduba_paper_implementation_20261031/ASSET_CPU2_RESULT.json)
- [research/feduba_paper_implementation_20261031/ASSET_CPU2_ONCE.json](feduba_paper_implementation_20261031/ASSET_CPU2_ONCE.json)
- [research/feduba_paper_implementation_20261031/STG_SGD_CPU_RESULT.json](feduba_paper_implementation_20261031/STG_SGD_CPU_RESULT.json)
- [research/feduba_paper_implementation_20261031/STG_LAUNCH_PROTOCOL.txt](feduba_paper_implementation_20261031/STG_LAUNCH_PROTOCOL.txt)
- [research/feduba_paper_implementation_20261031/STG_LAUNCH_PROFILE.json](feduba_paper_implementation_20261031/STG_LAUNCH_PROFILE.json)
- [research/feduba_paper_implementation_20261031/STG_FREEZE.json](feduba_paper_implementation_20261031/STG_FREEZE.json)
- [research/feduba_paper_implementation_20261031/STG_CONTROLLER_ONCE.json](feduba_paper_implementation_20261031/STG_CONTROLLER_ONCE.json)
- [research/feduba_paper_implementation_20261031/STG_READY.json](feduba_paper_implementation_20261031/STG_READY.json)
- [research/feduba_paper_implementation_20261031/FU_PROTOCOL.txt](feduba_paper_implementation_20261031/FU_PROTOCOL.txt)
- [research/feduba_paper_implementation_20261031/FU_PROFILE.json](feduba_paper_implementation_20261031/FU_PROFILE.json)
- [research/feduba_paper_implementation_20261031/FU_POLICY_CPU_FREEZE.json](feduba_paper_implementation_20261031/FU_POLICY_CPU_FREEZE.json)
- [research/feduba_paper_implementation_20261031/FU_POLICY_CPU_RESULT.json](feduba_paper_implementation_20261031/FU_POLICY_CPU_RESULT.json)
- [research/feduba_paper_implementation_20261031/SSS_PROTOCOL.txt](feduba_paper_implementation_20261031/SSS_PROTOCOL.txt)
- [research/feduba_paper_implementation_20261031/SSS_LOGGER_CPU_FREEZE.json](feduba_paper_implementation_20261031/SSS_LOGGER_CPU_FREEZE.json)
- [research/feduba_paper_implementation_20261031/SSS_LOGGER_CPU_RECOVERY_PROTOCOL.txt](feduba_paper_implementation_20261031/SSS_LOGGER_CPU_RECOVERY_PROTOCOL.txt)
- [research/feduba_paper_implementation_20261031/SSS_LOGGER_CPU2_FREEZE.json](feduba_paper_implementation_20261031/SSS_LOGGER_CPU2_FREEZE.json)
- [research/feduba_paper_implementation_20261031/incidents/sss_logger_cpu_v1/MANIFEST.json](feduba_paper_implementation_20261031/incidents/sss_logger_cpu_v1/MANIFEST.json)
- [research/feduba_paper_implementation_20261031/SSS_SOURCE_FREEZE.json](feduba_paper_implementation_20261031/SSS_SOURCE_FREEZE.json)
- [research/feduba_paper_implementation_20261031/SSS_LOGGER_CPU2_RESULT.json](feduba_paper_implementation_20261031/SSS_LOGGER_CPU2_RESULT.json)
- [research/feduba_paper_implementation_20261031/SSS_ROUNDOFF_DIAGNOSIS.json](feduba_paper_implementation_20261031/SSS_ROUNDOFF_DIAGNOSIS.json)
- [research/feduba_paper_implementation_20261031/FU_ENGINE_CPU_PROTOCOL.txt](feduba_paper_implementation_20261031/FU_ENGINE_CPU_PROTOCOL.txt)
- [research/feduba_paper_implementation_20261031/FU_ENGINE_CPU_FREEZE.json](feduba_paper_implementation_20261031/FU_ENGINE_CPU_FREEZE.json)
- [research/feduba_paper_implementation_20261031/FU_EXECUTION_CONTRACT.txt](feduba_paper_implementation_20261031/FU_EXECUTION_CONTRACT.txt)
- [research/feduba_paper_implementation_20261031/FU_SOURCE_FREEZE.json](feduba_paper_implementation_20261031/FU_SOURCE_FREEZE.json)
- [research/feduba_paper_implementation_20261031/FU_ENGINE_CPU_RESULT.json](feduba_paper_implementation_20261031/FU_ENGINE_CPU_RESULT.json)
- [research/feduba_paper_implementation_20261031/CLEAN_FL_RESULT.json](feduba_paper_implementation_20261031/CLEAN_FL_RESULT.json)
- [research/feduba_paper_implementation_20261031/CLEAN_DELIVERY_PROTOCOL.txt](feduba_paper_implementation_20261031/CLEAN_DELIVERY_PROTOCOL.txt)
- [research/feduba_paper_implementation_20261031/CLEAN_EXPORT_FREEZE.json](feduba_paper_implementation_20261031/CLEAN_EXPORT_FREEZE.json)
- [research/feduba_paper_implementation_20261031/CLEAN_FL_VERIFIED.json](feduba_paper_implementation_20261031/CLEAN_FL_VERIFIED.json)
- [research/feduba_paper_implementation_20261031/CLEAN_REVIEW_DELIVERY_REMOTE.json](feduba_paper_implementation_20261031/CLEAN_REVIEW_DELIVERY_REMOTE.json)
- [research/feduba_paper_implementation_20261031/CLEAN_RECEIVE_FREEZE.json](feduba_paper_implementation_20261031/CLEAN_RECEIVE_FREEZE.json)
- [research/feduba_paper_implementation_20261031/STG_STARTED.json](feduba_paper_implementation_20261031/STG_STARTED.json)
- [research/feduba_paper_implementation_20261031/CLEAN_REGISTRATION_FREEZE.json](feduba_paper_implementation_20261031/CLEAN_REGISTRATION_FREEZE.json)
- [research/feduba_paper_implementation_20261031/CLEAN_REVIEW_LOCAL_COMPLETE.json](feduba_paper_implementation_20261031/CLEAN_REVIEW_LOCAL_COMPLETE.json)
- [research/feduba_paper_implementation_20261031/CLEAN_DELIVERY_COMPLETE.json](feduba_paper_implementation_20261031/CLEAN_DELIVERY_COMPLETE.json)
- [research/feduba_paper_implementation_20261031/REGISTRATION_LAUNCH_FAILURE_v1.json](feduba_paper_implementation_20261031/REGISTRATION_LAUNCH_FAILURE_v1.json)
- [research/feduba_paper_implementation_20261031/registrations/clean_main/REGISTERED.json](feduba_paper_implementation_20261031/registrations/clean_main/REGISTERED.json)
- [research/feduba_paper_implementation_20261031/registrations/clean_pr/REGISTERED.json](feduba_paper_implementation_20261031/registrations/clean_pr/REGISTERED.json)
- [research/feduba_paper_implementation_20261031/registrations/clean_dislab/REGISTERED.json](feduba_paper_implementation_20261031/registrations/clean_dislab/REGISTERED.json)
- [research/feduba_paper_implementation_20261031/STG_STATE.json](feduba_paper_implementation_20261031/STG_STATE.json)
- [research/feduba_paper_implementation_20261031/PAIR_EVAL_PROTOCOL.txt](feduba_paper_implementation_20261031/PAIR_EVAL_PROTOCOL.txt)
- [research/feduba_paper_implementation_20261031/PAIR_EVAL_PROFILE.json](feduba_paper_implementation_20261031/PAIR_EVAL_PROFILE.json)
- [research/feduba_paper_implementation_20261031/PAIR_EVAL_CPU_FREEZE.json](feduba_paper_implementation_20261031/PAIR_EVAL_CPU_FREEZE.json)
- [research/feduba_paper_implementation_20261031/PAIR_EVAL_SOURCE_FREEZE.json](feduba_paper_implementation_20261031/PAIR_EVAL_SOURCE_FREEZE.json)
- [research/feduba_paper_implementation_20261031/PAIR_EVAL_CPU_RESULT.json](feduba_paper_implementation_20261031/PAIR_EVAL_CPU_RESULT.json)
- [research/feduba_paper_implementation_20261031/PAIR_EVAL_CPU_CHECKS.json](feduba_paper_implementation_20261031/PAIR_EVAL_CPU_CHECKS.json)
- [research/feduba_paper_implementation_20261031/PAIR_EVAL_CPU_ONCE.json](feduba_paper_implementation_20261031/PAIR_EVAL_CPU_ONCE.json)
- [research/feduba_paper_implementation_20261031/SSS_NUMERIC_POLICY.json](feduba_paper_implementation_20261031/SSS_NUMERIC_POLICY.json)
- [research/feduba_paper_implementation_20261031/SSS_NUMERIC_PROTOCOL.txt](feduba_paper_implementation_20261031/SSS_NUMERIC_PROTOCOL.txt)
- [research/feduba_paper_implementation_20261031/SSS_NUMERIC_SOURCE_CHECKS.json](feduba_paper_implementation_20261031/SSS_NUMERIC_SOURCE_CHECKS.json)
- [research/feduba_paper_implementation_20261031/PAIR_LAUNCH_PROTOCOL.txt](feduba_paper_implementation_20261031/PAIR_LAUNCH_PROTOCOL.txt)
- [research/feduba_paper_implementation_20261031/PAIR_PREPARE_FREEZE.json](feduba_paper_implementation_20261031/PAIR_PREPARE_FREEZE.json)
- [research/feduba_paper_implementation_20261031/STG_RESULT.json](feduba_paper_implementation_20261031/STG_RESULT.json)
- [research/feduba_paper_implementation_20261031/STG_AUDIT_FAILURE.json](feduba_paper_implementation_20261031/STG_AUDIT_FAILURE.json)
- [research/feduba_paper_implementation_20261031/incidents/stg_cpu_gradient_v1/MANIFEST.json](feduba_paper_implementation_20261031/incidents/stg_cpu_gradient_v1/MANIFEST.json)
- [research/feduba_paper_implementation_20261031/STG_GRAD_DIAG_PROTOCOL.txt](feduba_paper_implementation_20261031/STG_GRAD_DIAG_PROTOCOL.txt)
- [research/feduba_paper_implementation_20261031/STG_GRAD_DIAG_FREEZE.json](feduba_paper_implementation_20261031/STG_GRAD_DIAG_FREEZE.json)
- [research/feduba_paper_implementation_20261031/STG_GRAD_DIAG_RESULT.json](feduba_paper_implementation_20261031/STG_GRAD_DIAG_RESULT.json)
- [research/feduba_paper_implementation_20261031/STG_CPU_TRIGGER_PROTOCOL.txt](feduba_paper_implementation_20261031/STG_CPU_TRIGGER_PROTOCOL.txt)
- [research/feduba_paper_implementation_20261031/STG_CPU_TRIGGER_PROFILE.json](feduba_paper_implementation_20261031/STG_CPU_TRIGGER_PROFILE.json)
- [research/feduba_paper_implementation_20261031/STG_CPU_TRIGGER_FREEZE.json](feduba_paper_implementation_20261031/STG_CPU_TRIGGER_FREEZE.json)
- [research/feduba_paper_implementation_20261031/STG_CPU_TRIGGER_STARTED.json](feduba_paper_implementation_20261031/STG_CPU_TRIGGER_STARTED.json)
- [research/feduba_paper_implementation_20261031/STG_CPU_TRIGGER_RESULT.json](feduba_paper_implementation_20261031/STG_CPU_TRIGGER_RESULT.json)
- [research/feduba_paper_implementation_20261031/STG_CPU_TRIGGER_VERIFIED.json](feduba_paper_implementation_20261031/STG_CPU_TRIGGER_VERIFIED.json)
- [research/feduba_paper_implementation_20261031/STG_CPU_SOURCE_BINDING.json](feduba_paper_implementation_20261031/STG_CPU_SOURCE_BINDING.json)
- [research/feduba_paper_implementation_20261031/CPU_BINDING_LAUNCH_PROTOCOL.txt](feduba_paper_implementation_20261031/CPU_BINDING_LAUNCH_PROTOCOL.txt)
- [research/feduba_paper_implementation_20261031/SSS_LAUNCH_PROFILE.json](feduba_paper_implementation_20261031/SSS_LAUNCH_PROFILE.json)
- [research/feduba_paper_implementation_20261031/FU_LAUNCH_PROFILE.json](feduba_paper_implementation_20261031/FU_LAUNCH_PROFILE.json)
- [research/feduba_paper_implementation_20261031/PAIR_EVAL_LAUNCH_PROFILE.json](feduba_paper_implementation_20261031/PAIR_EVAL_LAUNCH_PROFILE.json)
- [research/feduba_paper_implementation_20261031/PAIR_LAUNCH_PROFILE.json](feduba_paper_implementation_20261031/PAIR_LAUNCH_PROFILE.json)
- [research/feduba_paper_implementation_20261031/SSS_FREEZE.json](feduba_paper_implementation_20261031/SSS_FREEZE.json)
- [research/feduba_paper_implementation_20261031/FU_RUN_FREEZE.json](feduba_paper_implementation_20261031/FU_RUN_FREEZE.json)
- [research/feduba_paper_implementation_20261031/PAIR_EVAL_RUN_FREEZE.json](feduba_paper_implementation_20261031/PAIR_EVAL_RUN_FREEZE.json)
- [research/feduba_paper_implementation_20261031/PAIR_RUN_FREEZE.json](feduba_paper_implementation_20261031/PAIR_RUN_FREEZE.json)
- [research/feduba_paper_implementation_20261031/PAIR_PREPARE_ONCE.json](feduba_paper_implementation_20261031/PAIR_PREPARE_ONCE.json)
- [research/feduba_paper_implementation_20261031/PAIR_PREPARE_RESULT.json](feduba_paper_implementation_20261031/PAIR_PREPARE_RESULT.json)
- [research/feduba_paper_implementation_20261031/PAIR_PUBLICATION.json](feduba_paper_implementation_20261031/PAIR_PUBLICATION.json)
- [research/feduba_paper_implementation_20261031/PAIR_STARTED.json](feduba_paper_implementation_20261031/PAIR_STARTED.json)
- [research/feduba_paper_implementation_20261031/SSS_COMPLETION_SUMMARY.json](feduba_paper_implementation_20261031/SSS_COMPLETION_SUMMARY.json)
- [research/feduba_paper_implementation_20261031/FU_benign_RESULT.json](feduba_paper_implementation_20261031/FU_benign_RESULT.json)
- [research/feduba_paper_implementation_20261031/FU_BENIGN_TRAINING_COMPLETE.json](feduba_paper_implementation_20261031/FU_BENIGN_TRAINING_COMPLETE.json)
- [research/feduba_paper_implementation_20261031/FU_benign_VERIFIED.json](feduba_paper_implementation_20261031/FU_benign_VERIFIED.json)
- [research/feduba_paper_implementation_20261031/FU_BENIGN_COMPLETION.json](feduba_paper_implementation_20261031/FU_BENIGN_COMPLETION.json)
- [research/feduba_paper_implementation_20261031/FU_attack_RESULT.json](feduba_paper_implementation_20261031/FU_attack_RESULT.json)
- [research/feduba_paper_implementation_20261031/FU_ATTACK_TRAINING_COMPLETE.json](feduba_paper_implementation_20261031/FU_ATTACK_TRAINING_COMPLETE.json)
- [research/feduba_paper_implementation_20261031/PAIR_DELIVERY_PROTOCOL.txt](feduba_paper_implementation_20261031/PAIR_DELIVERY_PROTOCOL.txt)
- [research/feduba_paper_implementation_20261031/FU_attack_VERIFIED.json](feduba_paper_implementation_20261031/FU_attack_VERIFIED.json)
- [research/feduba_paper_implementation_20261031/FU_ATTACK_COMPLETION.json](feduba_paper_implementation_20261031/FU_ATTACK_COMPLETION.json)
- [research/feduba_paper_implementation_20261031/PAIR_EVAL_RESULT.json](feduba_paper_implementation_20261031/PAIR_EVAL_RESULT.json)
- [research/feduba_paper_implementation_20261031/PAIR_EVAL_VERIFIED.json](feduba_paper_implementation_20261031/PAIR_EVAL_VERIFIED.json)
- [research/feduba_paper_implementation_20261031/PAIR_CONTROLLER_STATE.json](feduba_paper_implementation_20261031/PAIR_CONTROLLER_STATE.json)
- [research/feduba_paper_implementation_20261031/PAIR_EVALUATION_COMPLETION.json](feduba_paper_implementation_20261031/PAIR_EVALUATION_COMPLETION.json)
- [research/feduba_paper_implementation_20261031/PAIR_EVALUATION_REPORT_KO.txt](feduba_paper_implementation_20261031/PAIR_EVALUATION_REPORT_KO.txt)
- [research/feduba_paper_implementation_20261031/PAIR_REVIEW_EXECUTION_CONTRACT.txt](feduba_paper_implementation_20261031/PAIR_REVIEW_EXECUTION_CONTRACT.txt)
- [research/feduba_paper_implementation_20261031/PAIR_REVIEW_FREEZE.json](feduba_paper_implementation_20261031/PAIR_REVIEW_FREEZE.json)
- [research/feduba_paper_implementation_20261031/PAIR_REVIEW_SOURCE_CHECKS.json](feduba_paper_implementation_20261031/PAIR_REVIEW_SOURCE_CHECKS.json)
- [research/feduba_paper_implementation_20261031/PAIR_REVIEW_PUBLICATION.json](feduba_paper_implementation_20261031/PAIR_REVIEW_PUBLICATION.json)
- [research/feduba_paper_implementation_20261031/PAIR_REVIEW_EXPORT_ONCE.json](feduba_paper_implementation_20261031/PAIR_REVIEW_EXPORT_ONCE.json)
- [research/feduba_paper_implementation_20261031/PAIR_REVIEW_EXPORT_FAILURE.json](feduba_paper_implementation_20261031/PAIR_REVIEW_EXPORT_FAILURE.json)
- [research/feduba_paper_implementation_20261031/PAIR_REVIEW_FAILED_PREFIX.json](feduba_paper_implementation_20261031/PAIR_REVIEW_FAILED_PREFIX.json)
- [research/feduba_paper_implementation_20261031/incidents/pair_review_export_callback_v1/MANIFEST.json](feduba_paper_implementation_20261031/incidents/pair_review_export_callback_v1/MANIFEST.json)
- [research/feduba_paper_implementation_20261031/PAIR_REVIEW_RECOVERY_PROTOCOL.txt](feduba_paper_implementation_20261031/PAIR_REVIEW_RECOVERY_PROTOCOL.txt)
- [research/feduba_paper_implementation_20261031/PAIR_REVIEW_RECOVERY_FREEZE.json](feduba_paper_implementation_20261031/PAIR_REVIEW_RECOVERY_FREEZE.json)
- [research/feduba_paper_implementation_20261031/PAIR_REVIEW_RECOVERY_SOURCE_CHECKS.json](feduba_paper_implementation_20261031/PAIR_REVIEW_RECOVERY_SOURCE_CHECKS.json)
- [research/feduba_paper_implementation_20261031/PAIR_REVIEW_RECOVERY_PUBLICATION.json](feduba_paper_implementation_20261031/PAIR_REVIEW_RECOVERY_PUBLICATION.json)
- [research/feduba_paper_implementation_20261031/PAIR_REVIEW_RECOVERY_ONCE.json](feduba_paper_implementation_20261031/PAIR_REVIEW_RECOVERY_ONCE.json)
- [research/feduba_paper_implementation_20261031/PAIR_REVIEW_RECOVERY_RESULT.json](feduba_paper_implementation_20261031/PAIR_REVIEW_RECOVERY_RESULT.json)
- [research/feduba_paper_implementation_20261031/PAIR_REVIEW_DELIVERY_REMOTE.json](feduba_paper_implementation_20261031/PAIR_REVIEW_DELIVERY_REMOTE.json)
- [research/feduba_paper_implementation_20261031/PAIR_REVIEW_LOCAL_COMPLETE.json](feduba_paper_implementation_20261031/PAIR_REVIEW_LOCAL_COMPLETE.json)
- [research/feduba_paper_implementation_20261031/PAIR_DELIVERY_COMPLETE.json](feduba_paper_implementation_20261031/PAIR_DELIVERY_COMPLETE.json)
- [research/feduba_paper_implementation_20261031/PAIR_DELIVERY_REPORT_KO.txt](feduba_paper_implementation_20261031/PAIR_DELIVERY_REPORT_KO.txt)
- [research/feduba_paper_implementation_20261031/registrations/pair_main/REGISTERED.json](feduba_paper_implementation_20261031/registrations/pair_main/REGISTERED.json)
- [research/feduba_paper_implementation_20261031/registrations/pair_pr/REGISTERED.json](feduba_paper_implementation_20261031/registrations/pair_pr/REGISTERED.json)
- [research/feduba_paper_implementation_20261031/registrations/pair_dislab/REGISTERED.json](feduba_paper_implementation_20261031/registrations/pair_dislab/REGISTERED.json)
- [research/feduba_paper_implementation_20261031/PAIR_CATALOGUE_FORMAT_CHECKS.json](feduba_paper_implementation_20261031/PAIR_CATALOGUE_FORMAT_CHECKS.json)
- [research/feduba_stage_diagnosis_20261101/PROTOCOL.txt](feduba_stage_diagnosis_20261101/PROTOCOL.txt)
- [research/feduba_stage_diagnosis_20261101/PROFILE.json](feduba_stage_diagnosis_20261101/PROFILE.json)
- [research/feduba_stage_diagnosis_20261101/FREEZE.json](feduba_stage_diagnosis_20261101/FREEZE.json)
- [research/feduba_stage_diagnosis_20261101/SOURCE_CHECKS.json](feduba_stage_diagnosis_20261101/SOURCE_CHECKS.json)
- [research/feduba_stage_diagnosis_20261101/REPORT_KO.txt](feduba_stage_diagnosis_20261101/REPORT_KO.txt)
- [research/feduba_stage_diagnosis_20261101/LAUNCH_INVOCATION_FAILURE.json](feduba_stage_diagnosis_20261101/LAUNCH_INVOCATION_FAILURE.json)
- [research/feduba_stage_diagnosis_20261101/LAUNCH_INVOCATION_RECOVERY.txt](feduba_stage_diagnosis_20261101/LAUNCH_INVOCATION_RECOVERY.txt)
- [research/feduba_stage_diagnosis_20261101/PUBLICATION.json](feduba_stage_diagnosis_20261101/PUBLICATION.json)
- [research/feduba_stage_diagnosis_20261101/RESULT.json](feduba_stage_diagnosis_20261101/RESULT.json)
- [research/feduba_stage_diagnosis_20261101/VERIFIED.json](feduba_stage_diagnosis_20261101/VERIFIED.json)
- [research/feduba_stage_diagnosis_20261101/TERMINAL_PROCESS.json](feduba_stage_diagnosis_20261101/TERMINAL_PROCESS.json)
- [research/feduba_stage_diagnosis_20261101/SAVED_STAGE_REVIEW.json](feduba_stage_diagnosis_20261101/SAVED_STAGE_REVIEW.json)
- [research/feduba_stage_diagnosis_20261101/COMPLETION.json](feduba_stage_diagnosis_20261101/COMPLETION.json)
- [research/feduba_stage_diagnosis_20261101/NEXT_CURRICULUM_RATIONALE.txt](feduba_stage_diagnosis_20261101/NEXT_CURRICULUM_RATIONALE.txt)
- [research/feduba_stage_diagnosis_20261101/CHECKS.json](feduba_stage_diagnosis_20261101/CHECKS.json)
- [research/feduba_mixed_surrogate_20261101/PROTOCOL.txt](feduba_mixed_surrogate_20261101/PROTOCOL.txt)
- [research/feduba_mixed_surrogate_20261101/PROFILE.json](feduba_mixed_surrogate_20261101/PROFILE.json)
- [research/feduba_mixed_surrogate_20261101/FREEZE.json](feduba_mixed_surrogate_20261101/FREEZE.json)
- [research/feduba_mixed_surrogate_20261101/MONITOR_PROTOCOL.txt](feduba_mixed_surrogate_20261101/MONITOR_PROTOCOL.txt)
- [research/feduba_mixed_surrogate_20261101/COPY_PROVENANCE.json](feduba_mixed_surrogate_20261101/COPY_PROVENANCE.json)
- [research/feduba_mixed_surrogate_20261101/SOURCE_CHECKS.json](feduba_mixed_surrogate_20261101/SOURCE_CHECKS.json)
- [research/feduba_mixed_surrogate_20261101/REPORT_KO.txt](feduba_mixed_surrogate_20261101/REPORT_KO.txt)
- [research/feduba_mixed_surrogate_20261101/PUBLICATION.json](feduba_mixed_surrogate_20261101/PUBLICATION.json)
- [research/feduba_mixed_surrogate_20261101/CONTROLLER_ONCE.json](feduba_mixed_surrogate_20261101/CONTROLLER_ONCE.json)
- [research/feduba_mixed_surrogate_20261101/TRAIN_ONCE.json](feduba_mixed_surrogate_20261101/TRAIN_ONCE.json)
- [research/feduba_mixed_surrogate_20261101/NORMAL_SELECTION.json](feduba_mixed_surrogate_20261101/NORMAL_SELECTION.json)
- [research/feduba_mixed_surrogate_20261101/DOMAIN_CONTRACT_ONCE.json](feduba_mixed_surrogate_20261101/DOMAIN_CONTRACT_ONCE.json)
- [research/feduba_mixed_surrogate_20261101/DOMAIN_CONTRACT_RESULT.json](feduba_mixed_surrogate_20261101/DOMAIN_CONTRACT_RESULT.json)
- [research/feduba_mixed_surrogate_20261101/STARTED_OBSERVATION.json](feduba_mixed_surrogate_20261101/STARTED_OBSERVATION.json)
- [research/feduba_mixed_surrogate_20261101/CHECKS.json](feduba_mixed_surrogate_20261101/CHECKS.json)
- [research/feduba_mixed_surrogate_20261101/LIVE_SOURCE_CHECKS.json](feduba_mixed_surrogate_20261101/LIVE_SOURCE_CHECKS.json)
- [research/feduba_mixed_trigger_20261101/SOURCE_PROFILE.json](feduba_mixed_trigger_20261101/SOURCE_PROFILE.json)
- [research/feduba_mixed_trigger_20261101/SOURCE_FREEZE.json](feduba_mixed_trigger_20261101/SOURCE_FREEZE.json)
- [research/feduba_mixed_trigger_20261101/PROTOCOL.txt](feduba_mixed_trigger_20261101/PROTOCOL.txt)
- [research/feduba_mixed_trigger_20261101/MONITOR_PROTOCOL.txt](feduba_mixed_trigger_20261101/MONITOR_PROTOCOL.txt)
- [research/feduba_mixed_trigger_20261101/COPY_PROVENANCE.json](feduba_mixed_trigger_20261101/COPY_PROVENANCE.json)
- [research/feduba_mixed_trigger_20261101/SOURCE_ONLY_REVIEW.json](feduba_mixed_trigger_20261101/SOURCE_ONLY_REVIEW.json)
- [research/feduba_mixed_trigger_20261101/REPORT_KO.txt](feduba_mixed_trigger_20261101/REPORT_KO.txt)
- [research/feduba_mixed_trigger_20261101/SOURCE_PUBLICATION.json](feduba_mixed_trigger_20261101/SOURCE_PUBLICATION.json)
- [research/feduba_mixed_surrogate_20261101/TRAIN_RESULT.json](feduba_mixed_surrogate_20261101/TRAIN_RESULT.json)
- [research/feduba_mixed_surrogate_20261101/TRAIN_VERIFIED.json](feduba_mixed_surrogate_20261101/TRAIN_VERIFIED.json)
- [research/feduba_mixed_surrogate_20261101/ENDPOINT_RESULT.json](feduba_mixed_surrogate_20261101/ENDPOINT_RESULT.json)
- [research/feduba_mixed_surrogate_20261101/ENDPOINT_VERIFIED.json](feduba_mixed_surrogate_20261101/ENDPOINT_VERIFIED.json)
- [research/feduba_mixed_surrogate_20261101/COMPLETION.json](feduba_mixed_surrogate_20261101/COMPLETION.json)
- [research/feduba_mixed_surrogate_20261101/MANIFEST.json](feduba_mixed_surrogate_20261101/MANIFEST.json)
- [research/feduba_mixed_surrogate_20261101/TERMINAL_OBSERVATION.json](feduba_mixed_surrogate_20261101/TERMINAL_OBSERVATION.json)
- [research/feduba_mixed_surrogate_20261101/COMPLETION_REPORT_KO.txt](feduba_mixed_surrogate_20261101/COMPLETION_REPORT_KO.txt)
- [research/feduba_mixed_trigger_20261101/PREPARE_ONCE.json](feduba_mixed_trigger_20261101/PREPARE_ONCE.json)
- [research/feduba_mixed_trigger_20261101/PREPARE_RESULT.json](feduba_mixed_trigger_20261101/PREPARE_RESULT.json)
- [research/feduba_mixed_trigger_20261101/TEACHER_TERMINAL.json](feduba_mixed_trigger_20261101/TEACHER_TERMINAL.json)
- [research/feduba_mixed_trigger_20261101/NORMAL_SELECTION.json](feduba_mixed_trigger_20261101/NORMAL_SELECTION.json)
- [research/feduba_mixed_trigger_20261101/LAUNCH_PROFILE.json](feduba_mixed_trigger_20261101/LAUNCH_PROFILE.json)
- [research/feduba_mixed_trigger_20261101/RUN_FREEZE.json](feduba_mixed_trigger_20261101/RUN_FREEZE.json)
- [research/feduba_mixed_trigger_20261101/LAUNCH_BINDING_CHECKS.json](feduba_mixed_trigger_20261101/LAUNCH_BINDING_CHECKS.json)
- [research/feduba_mixed_trigger_20261101/RUN_PUBLICATION.json](feduba_mixed_trigger_20261101/RUN_PUBLICATION.json)
- [research/feduba_mixed_trigger_20261101/STARTED_OBSERVATION.json](feduba_mixed_trigger_20261101/STARTED_OBSERVATION.json)
- [research/feduba_mixed_trigger_20261101/CONTROLLER_ONCE.json](feduba_mixed_trigger_20261101/CONTROLLER_ONCE.json)
- [research/feduba_mixed_trigger_20261101/TRIGGER_ONCE.json](feduba_mixed_trigger_20261101/TRIGGER_ONCE.json)
- [research/feduba_mixed_pair_20261101/PROTOCOL.txt](feduba_mixed_pair_20261101/PROTOCOL.txt)
- [research/feduba_mixed_pair_20261101/SOURCE_PROFILE.json](feduba_mixed_pair_20261101/SOURCE_PROFILE.json)
- [research/feduba_mixed_pair_20261101/SOURCE_FREEZE.json](feduba_mixed_pair_20261101/SOURCE_FREEZE.json)
- [research/feduba_mixed_pair_20261101/COPY_PROVENANCE.json](feduba_mixed_pair_20261101/COPY_PROVENANCE.json)
- [research/feduba_mixed_pair_20261101/MONITOR_PROTOCOL.txt](feduba_mixed_pair_20261101/MONITOR_PROTOCOL.txt)
- [research/feduba_mixed_pair_20261101/REPORT_KO.txt](feduba_mixed_pair_20261101/REPORT_KO.txt)
- [research/feduba_mixed_trigger_20261101/TRIGGER_RESULT.json](feduba_mixed_trigger_20261101/TRIGGER_RESULT.json)
- [research/feduba_mixed_trigger_20261101/TRIGGER_VERIFIED.json](feduba_mixed_trigger_20261101/TRIGGER_VERIFIED.json)
- [research/feduba_mixed_trigger_20261101/COMPLETION.json](feduba_mixed_trigger_20261101/COMPLETION.json)
- [research/feduba_mixed_trigger_20261101/MANIFEST.json](feduba_mixed_trigger_20261101/MANIFEST.json)
- [research/feduba_mixed_trigger_20261101/COMPLETION_REPORT_KO.txt](feduba_mixed_trigger_20261101/COMPLETION_REPORT_KO.txt)
- [research/feduba_mixed_pair_20261101/SOURCE_ONLY_REVIEW.json](feduba_mixed_pair_20261101/SOURCE_ONLY_REVIEW.json)
- [research/feduba_mixed_pair_20261101/SOURCE_PUBLICATION.json](feduba_mixed_pair_20261101/SOURCE_PUBLICATION.json)
- [research/feduba_mixed_pair_20261101/PREPARE_ONCE.json](feduba_mixed_pair_20261101/PREPARE_ONCE.json)
- [research/feduba_mixed_pair_20261101/PREPARE_RESULT.json](feduba_mixed_pair_20261101/PREPARE_RESULT.json)
- [research/feduba_mixed_pair_20261101/TRIGGER_SOURCE_BINDING.json](feduba_mixed_pair_20261101/TRIGGER_SOURCE_BINDING.json)
- [research/feduba_mixed_pair_20261101/TRIGGER_TERMINAL.json](feduba_mixed_pair_20261101/TRIGGER_TERMINAL.json)
- [research/feduba_mixed_pair_20261101/NORMAL_SELECTION.json](feduba_mixed_pair_20261101/NORMAL_SELECTION.json)
- [research/feduba_mixed_pair_20261101/SSS_LAUNCH_PROFILE.json](feduba_mixed_pair_20261101/SSS_LAUNCH_PROFILE.json)
- [research/feduba_mixed_pair_20261101/FU_LAUNCH_PROFILE.json](feduba_mixed_pair_20261101/FU_LAUNCH_PROFILE.json)
- [research/feduba_mixed_pair_20261101/PAIR_EVAL_LAUNCH_PROFILE.json](feduba_mixed_pair_20261101/PAIR_EVAL_LAUNCH_PROFILE.json)
- [research/feduba_mixed_pair_20261101/PAIR_LAUNCH_PROFILE.json](feduba_mixed_pair_20261101/PAIR_LAUNCH_PROFILE.json)
- [research/feduba_mixed_pair_20261101/SSS_FREEZE.json](feduba_mixed_pair_20261101/SSS_FREEZE.json)
- [research/feduba_mixed_pair_20261101/FU_RUN_FREEZE.json](feduba_mixed_pair_20261101/FU_RUN_FREEZE.json)
- [research/feduba_mixed_pair_20261101/PAIR_EVAL_RUN_FREEZE.json](feduba_mixed_pair_20261101/PAIR_EVAL_RUN_FREEZE.json)
- [research/feduba_mixed_pair_20261101/PAIR_RUN_FREEZE.json](feduba_mixed_pair_20261101/PAIR_RUN_FREEZE.json)
- [research/feduba_mixed_pair_20261101/PREPUBLICATION_CHECKS.json](feduba_mixed_pair_20261101/PREPUBLICATION_CHECKS.json)
- [research/feduba_mixed_pair_20261101/PAIR_PUBLICATION.json](feduba_mixed_pair_20261101/PAIR_PUBLICATION.json)
- [research/feduba_mixed_pair_20261101/PAIR_CONTROLLER_ONCE.json](feduba_mixed_pair_20261101/PAIR_CONTROLLER_ONCE.json)
- [research/feduba_mixed_pair_20261101/SSS_ONCE.json](feduba_mixed_pair_20261101/SSS_ONCE.json)
- [research/feduba_mixed_pair_20261101/STARTED_OBSERVATION.json](feduba_mixed_pair_20261101/STARTED_OBSERVATION.json)
- [research/feduba_mixed_pair_20261101/SSS_COMPLETION_SUMMARY.json](feduba_mixed_pair_20261101/SSS_COMPLETION_SUMMARY.json)
- [research/feduba_mixed_monitor_20261101/PROTOCOL.txt](feduba_mixed_monitor_20261101/PROTOCOL.txt)
- [research/feduba_mixed_monitor_20261101/INCIDENT.json](feduba_mixed_monitor_20261101/INCIDENT.json)
- [research/feduba_mixed_monitor_20261101/FREEZE.json](feduba_mixed_monitor_20261101/FREEZE.json)
- [research/feduba_mixed_monitor_20261101/FIRST_PROBE_FAILURE.json](feduba_mixed_monitor_20261101/FIRST_PROBE_FAILURE.json)
- [research/feduba_mixed_monitor_20261101/RECOVERY_V2_PROTOCOL.txt](feduba_mixed_monitor_20261101/RECOVERY_V2_PROTOCOL.txt)
- [research/feduba_mixed_monitor_20261101/FREEZE_V2.json](feduba_mixed_monitor_20261101/FREEZE_V2.json)
- [research/feduba_mixed_monitor_20261101/BOUNDED_OBSERVATION_V2.json](feduba_mixed_monitor_20261101/BOUNDED_OBSERVATION_V2.json)
- [research/feduba_mixed_monitor_20261101/ACTIVE_FREEZE_CHECKS.json](feduba_mixed_monitor_20261101/ACTIVE_FREEZE_CHECKS.json)
- [research/feduba_mixed_monitor_20261101/REPORT_KO.txt](feduba_mixed_monitor_20261101/REPORT_KO.txt)
- [research/feduba_mixed_pair_20261101/FU_benign_RESULT.json](feduba_mixed_pair_20261101/FU_benign_RESULT.json)
- [research/feduba_mixed_pair_20261101/BENIGN_TRAIN_COMPLETION_OBSERVATION.json](feduba_mixed_pair_20261101/BENIGN_TRAIN_COMPLETION_OBSERVATION.json)
- [research/feduba_mixed_pair_20261101/BENIGN_TRAIN_COMPLETION_SUMMARY.json](feduba_mixed_pair_20261101/BENIGN_TRAIN_COMPLETION_SUMMARY.json)
- [research/feduba_mixed_pair_20261101/FU_benign_VERIFIED.json](feduba_mixed_pair_20261101/FU_benign_VERIFIED.json)
- [research/feduba_mixed_pair_20261101/BENIGN_AUDIT_COPY_CHECKS.json](feduba_mixed_pair_20261101/BENIGN_AUDIT_COPY_CHECKS.json)
- [research/feduba_mixed_pair_20261101/BENIGN_AUDIT_COMPLETION_OBSERVATION.json](feduba_mixed_pair_20261101/BENIGN_AUDIT_COMPLETION_OBSERVATION.json)
- [research/feduba_mixed_pair_20261101/BENIGN_AUDIT_COMPLETION_SUMMARY.json](feduba_mixed_pair_20261101/BENIGN_AUDIT_COMPLETION_SUMMARY.json)
- [research/feduba_mixed_pair_20261101/ATTACK_STARTED_OBSERVATION.json](feduba_mixed_pair_20261101/ATTACK_STARTED_OBSERVATION.json)
- [research/feduba_mixed_pair_memory_recovery_20261101/ATTACK_MEMORY_FAILURE_OBSERVATION.json](feduba_mixed_pair_memory_recovery_20261101/ATTACK_MEMORY_FAILURE_OBSERVATION.json)
- [research/feduba_mixed_pair_memory_recovery_20261101/FU_attack_FAILURE.json](feduba_mixed_pair_memory_recovery_20261101/FU_attack_FAILURE.json)
- [research/feduba_mixed_pair_memory_recovery_20261101/OPS_PROFILE.json](feduba_mixed_pair_memory_recovery_20261101/OPS_PROFILE.json)
- [research/feduba_mixed_pair_memory_recovery_20261101/OWN_OBSERVER_IDENTITY.json](feduba_mixed_pair_memory_recovery_20261101/OWN_OBSERVER_IDENTITY.json)
- [research/feduba_mixed_pair_memory_recovery_20261101/PAIR_CONTROLLER_FAILURE.json](feduba_mixed_pair_memory_recovery_20261101/PAIR_CONTROLLER_FAILURE.json)
- [research/feduba_mixed_pair_memory_recovery_20261101/preserve_prefix.py](feduba_mixed_pair_memory_recovery_20261101/preserve_prefix.py)
- [research/feduba_mixed_pair_memory_recovery_20261101/PROTOCOL.txt](feduba_mixed_pair_memory_recovery_20261101/PROTOCOL.txt)
- [research/feduba_mixed_pair_memory_recovery_20261101/REPORT_KO.txt](feduba_mixed_pair_memory_recovery_20261101/REPORT_KO.txt)
- [research/feduba_mixed_pair_memory_recovery_20261101/SOURCE_CHECKS.json](feduba_mixed_pair_memory_recovery_20261101/SOURCE_CHECKS.json)
- [research/feduba_mixed_pair_memory_recovery_20261101/SOURCE_FREEZE.json](feduba_mixed_pair_memory_recovery_20261101/SOURCE_FREEZE.json)
- [research/feduba_mixed_pair_memory_recovery_20261101/STOP_OWN_OBSERVER.ps1](feduba_mixed_pair_memory_recovery_20261101/STOP_OWN_OBSERVER.ps1)
- [research/feduba_mixed_pair_memory_recovery_20261101/TERMINAL_SYSTEM_SUMMARY.json](feduba_mixed_pair_memory_recovery_20261101/TERMINAL_SYSTEM_SUMMARY.json)
- [research/feduba_mixed_pair_memory_recovery_20261101/PUBLICATION.json](feduba_mixed_pair_memory_recovery_20261101/PUBLICATION.json)
- [research/feduba_mixed_pair_memory_recovery_20261101/OPS_ONCE.json](feduba_mixed_pair_memory_recovery_20261101/OPS_ONCE.json)
- [research/feduba_mixed_pair_memory_recovery_20261101/OPS_RESULT.json](feduba_mixed_pair_memory_recovery_20261101/OPS_RESULT.json)
- [research/feduba_mixed_pair_memory_recovery_20261101/PREFIX_LAUNCH_INVOCATION_FAILURE.json](feduba_mixed_pair_memory_recovery_20261101/PREFIX_LAUNCH_INVOCATION_FAILURE.json)
- [research/feduba_mixed_pair_memory_recovery_20261101/PREFIX_LAUNCH_PROTOCOL.txt](feduba_mixed_pair_memory_recovery_20261101/PREFIX_LAUNCH_PROTOCOL.txt)
- [research/feduba_mixed_pair_memory_recovery_20261101/launch_prefix_task.ps1](feduba_mixed_pair_memory_recovery_20261101/launch_prefix_task.ps1)
- [research/feduba_mixed_pair_memory_recovery_20261101/INVOCATION_FREEZE.json](feduba_mixed_pair_memory_recovery_20261101/INVOCATION_FREEZE.json)
- [research/feduba_mixed_pair_memory_recovery_20261101/PREFIX_LAUNCH_PUBLICATION.json](feduba_mixed_pair_memory_recovery_20261101/PREFIX_LAUNCH_PUBLICATION.json)
- [research/feduba_mixed_pair_memory_recovery_20261101/PREFIX_ONCE.json](feduba_mixed_pair_memory_recovery_20261101/PREFIX_ONCE.json)
- [research/feduba_mixed_pair_memory_recovery_20261101/PREFIX_PRESERVED.json](feduba_mixed_pair_memory_recovery_20261101/PREFIX_PRESERVED.json)
- [research/feduba_mixed_pair_memory_recovery_20261101/PREFIX_TASK_LAUNCH_ONCE.json](feduba_mixed_pair_memory_recovery_20261101/PREFIX_TASK_LAUNCH_ONCE.json)
- [research/feduba_mixed_pair_memory_recovery_20261101/PRESERVATION_TERMINAL_CHECKS.json](feduba_mixed_pair_memory_recovery_20261101/PRESERVATION_TERMINAL_CHECKS.json)
- [research/feduba_mixed_pair_memory_recovery_20261101/NEXT_RECOVERY_RATIONALE.txt](feduba_mixed_pair_memory_recovery_20261101/NEXT_RECOVERY_RATIONALE.txt)
- [research/feduba_mixed_attack_resume_20261101/audit_common.py](feduba_mixed_attack_resume_20261101/audit_common.py)
- [research/feduba_mixed_attack_resume_20261101/AUDIT_INPUT_BINDING.json](feduba_mixed_attack_resume_20261101/AUDIT_INPUT_BINDING.json)
- [research/feduba_mixed_attack_resume_20261101/COPY_PROVENANCE.json](feduba_mixed_attack_resume_20261101/COPY_PROVENANCE.json)
- [research/feduba_mixed_attack_resume_20261101/CPU_AUDIT_FREEZE.json](feduba_mixed_attack_resume_20261101/CPU_AUDIT_FREEZE.json)
- [research/feduba_mixed_attack_resume_20261101/CPU_AUDIT_PROFILE.json](feduba_mixed_attack_resume_20261101/CPU_AUDIT_PROFILE.json)
- [research/feduba_mixed_attack_resume_20261101/launch_cpu_audit.ps1](feduba_mixed_attack_resume_20261101/launch_cpu_audit.ps1)
- [research/feduba_mixed_attack_resume_20261101/MONITOR_PROTOCOL.txt](feduba_mixed_attack_resume_20261101/MONITOR_PROTOCOL.txt)
- [research/feduba_mixed_attack_resume_20261101/observe_cpu_status.py](feduba_mixed_attack_resume_20261101/observe_cpu_status.py)
- [research/feduba_mixed_attack_resume_20261101/PROTOCOL.txt](feduba_mixed_attack_resume_20261101/PROTOCOL.txt)
- [research/feduba_mixed_attack_resume_20261101/QUERY_CPU_STATUS.ps1](feduba_mixed_attack_resume_20261101/QUERY_CPU_STATUS.ps1)
- [research/feduba_mixed_attack_resume_20261101/REPORT_KO.txt](feduba_mixed_attack_resume_20261101/REPORT_KO.txt)
- [research/feduba_mixed_attack_resume_20261101/SOURCE_CHECKS.json](feduba_mixed_attack_resume_20261101/SOURCE_CHECKS.json)
- [research/feduba_mixed_attack_resume_20261101/verify_prefix.py](feduba_mixed_attack_resume_20261101/verify_prefix.py)
- [research/feduba_mixed_attack_resume_20261101/CPU_AUDIT_PUBLICATION.json](feduba_mixed_attack_resume_20261101/CPU_AUDIT_PUBLICATION.json)
- [research/feduba_mixed_attack_resume_20261101/STARTED_OBSERVATION.json](feduba_mixed_attack_resume_20261101/STARTED_OBSERVATION.json)
- [research/feduba_mixed_attack_resume_20261101/TASK_LAUNCH_ONCE.json](feduba_mixed_attack_resume_20261101/TASK_LAUNCH_ONCE.json)
- [research/feduba_mixed_attack_resume_20261101/AUDIT_FAILURE.json](feduba_mixed_attack_resume_20261101/AUDIT_FAILURE.json)
- [research/feduba_mixed_attack_resume_20261101/AUDIT_FAILURE_TERMINAL.json](feduba_mixed_attack_resume_20261101/AUDIT_FAILURE_TERMINAL.json)
- [research/feduba_mixed_attack_prefix_guard_v2_20261101/audit_common.py](feduba_mixed_attack_prefix_guard_v2_20261101/audit_common.py)
- [research/feduba_mixed_attack_prefix_guard_v2_20261101/AUDIT_INPUT_BINDING.json](feduba_mixed_attack_prefix_guard_v2_20261101/AUDIT_INPUT_BINDING.json)
- [research/feduba_mixed_attack_prefix_guard_v2_20261101/COPY_PROVENANCE.json](feduba_mixed_attack_prefix_guard_v2_20261101/COPY_PROVENANCE.json)
- [research/feduba_mixed_attack_prefix_guard_v2_20261101/CPU_AUDIT_FREEZE.json](feduba_mixed_attack_prefix_guard_v2_20261101/CPU_AUDIT_FREEZE.json)
- [research/feduba_mixed_attack_prefix_guard_v2_20261101/CPU_AUDIT_PROFILE.json](feduba_mixed_attack_prefix_guard_v2_20261101/CPU_AUDIT_PROFILE.json)
- [research/feduba_mixed_attack_prefix_guard_v2_20261101/launch_cpu_audit.ps1](feduba_mixed_attack_prefix_guard_v2_20261101/launch_cpu_audit.ps1)
- [research/feduba_mixed_attack_prefix_guard_v2_20261101/MONITOR_PROTOCOL.txt](feduba_mixed_attack_prefix_guard_v2_20261101/MONITOR_PROTOCOL.txt)
- [research/feduba_mixed_attack_prefix_guard_v2_20261101/native_memory.py](feduba_mixed_attack_prefix_guard_v2_20261101/native_memory.py)
- [research/feduba_mixed_attack_prefix_guard_v2_20261101/observe_cpu_status.py](feduba_mixed_attack_prefix_guard_v2_20261101/observe_cpu_status.py)
- [research/feduba_mixed_attack_prefix_guard_v2_20261101/PRIOR_GUARD_FAILURE.json](feduba_mixed_attack_prefix_guard_v2_20261101/PRIOR_GUARD_FAILURE.json)
- [research/feduba_mixed_attack_prefix_guard_v2_20261101/PRIOR_GUARD_TERMINAL.json](feduba_mixed_attack_prefix_guard_v2_20261101/PRIOR_GUARD_TERMINAL.json)
- [research/feduba_mixed_attack_prefix_guard_v2_20261101/PROTOCOL.txt](feduba_mixed_attack_prefix_guard_v2_20261101/PROTOCOL.txt)
- [research/feduba_mixed_attack_prefix_guard_v2_20261101/QUERY_CPU_STATUS.ps1](feduba_mixed_attack_prefix_guard_v2_20261101/QUERY_CPU_STATUS.ps1)
- [research/feduba_mixed_attack_prefix_guard_v2_20261101/REPORT_KO.txt](feduba_mixed_attack_prefix_guard_v2_20261101/REPORT_KO.txt)
- [research/feduba_mixed_attack_prefix_guard_v2_20261101/SOURCE_CHECKS.json](feduba_mixed_attack_prefix_guard_v2_20261101/SOURCE_CHECKS.json)
- [research/feduba_mixed_attack_prefix_guard_v2_20261101/verify_prefix.py](feduba_mixed_attack_prefix_guard_v2_20261101/verify_prefix.py)
- [research/feduba_mixed_attack_prefix_guard_v2_20261101/CPU_AUDIT_PUBLICATION.json](feduba_mixed_attack_prefix_guard_v2_20261101/CPU_AUDIT_PUBLICATION.json)
- [research/feduba_mixed_attack_prefix_guard_v2_20261101/AUDIT_RESULT.json](feduba_mixed_attack_prefix_guard_v2_20261101/AUDIT_RESULT.json)
- [research/feduba_mixed_attack_prefix_guard_v2_20261101/AUDIT_ONCE.json](feduba_mixed_attack_prefix_guard_v2_20261101/AUDIT_ONCE.json)
- [research/feduba_mixed_attack_prefix_guard_v2_20261101/TASK_LAUNCH_ONCE.json](feduba_mixed_attack_prefix_guard_v2_20261101/TASK_LAUNCH_ONCE.json)
- [research/feduba_mixed_attack_prefix_guard_v2_20261101/TERMINAL_CHECKS.json](feduba_mixed_attack_prefix_guard_v2_20261101/TERMINAL_CHECKS.json)
- [research/feduba_mixed_attack_prefix_guard_v2_20261101/COMPLETION_OBSERVATION.json](feduba_mixed_attack_prefix_guard_v2_20261101/COMPLETION_OBSERVATION.json)
- [research/feduba_mixed_attack_prefix_guard_v2_20261101/NEXT_GPU_RECOVERY_DESIGN.txt](feduba_mixed_attack_prefix_guard_v2_20261101/NEXT_GPU_RECOVERY_DESIGN.txt)
- [research/feduba_mixed_attack_recovery_run_20261101/.gitattributes](feduba_mixed_attack_recovery_run_20261101/.gitattributes)
- [research/feduba_mixed_attack_recovery_run_20261101/.gitignore](feduba_mixed_attack_recovery_run_20261101/.gitignore)
- [research/feduba_mixed_attack_recovery_run_20261101/COPY_PROVENANCE.json](feduba_mixed_attack_recovery_run_20261101/COPY_PROVENANCE.json)
- [research/feduba_mixed_attack_recovery_run_20261101/core.py](feduba_mixed_attack_recovery_run_20261101/core.py)
- [research/feduba_mixed_attack_recovery_run_20261101/ENTRYPOINT_ROUTING_REVIEW.json](feduba_mixed_attack_recovery_run_20261101/ENTRYPOINT_ROUTING_REVIEW.json)
- [research/feduba_mixed_attack_recovery_run_20261101/evaluate_pair.py](feduba_mixed_attack_recovery_run_20261101/evaluate_pair.py)
- [research/feduba_mixed_attack_recovery_run_20261101/fu_core.py](feduba_mixed_attack_recovery_run_20261101/fu_core.py)
- [research/feduba_mixed_attack_recovery_run_20261101/fu_training.py](feduba_mixed_attack_recovery_run_20261101/fu_training.py)
- [research/feduba_mixed_attack_recovery_run_20261101/launch_prepare.ps1](feduba_mixed_attack_recovery_run_20261101/launch_prepare.ps1)
- [research/feduba_mixed_attack_recovery_run_20261101/launch_recovery.ps1](feduba_mixed_attack_recovery_run_20261101/launch_recovery.ps1)
- [research/feduba_mixed_attack_recovery_run_20261101/model_reference.py](feduba_mixed_attack_recovery_run_20261101/model_reference.py)
- [research/feduba_mixed_attack_recovery_run_20261101/MONITOR_PROTOCOL.txt](feduba_mixed_attack_recovery_run_20261101/MONITOR_PROTOCOL.txt)
- [research/feduba_mixed_attack_recovery_run_20261101/native_memory.py](feduba_mixed_attack_recovery_run_20261101/native_memory.py)
- [research/feduba_mixed_attack_recovery_run_20261101/observe_status.py](feduba_mixed_attack_recovery_run_20261101/observe_status.py)
- [research/feduba_mixed_attack_recovery_run_20261101/pair_binding.py](feduba_mixed_attack_recovery_run_20261101/pair_binding.py)
- [research/feduba_mixed_attack_recovery_run_20261101/pair_eval_core.py](feduba_mixed_attack_recovery_run_20261101/pair_eval_core.py)
- [research/feduba_mixed_attack_recovery_run_20261101/prepare_launch.py](feduba_mixed_attack_recovery_run_20261101/prepare_launch.py)
- [research/feduba_mixed_attack_recovery_run_20261101/PROTOCOL.txt](feduba_mixed_attack_recovery_run_20261101/PROTOCOL.txt)
- [research/feduba_mixed_attack_recovery_run_20261101/QUERY_STATUS.ps1](feduba_mixed_attack_recovery_run_20261101/QUERY_STATUS.ps1)
- [research/feduba_mixed_attack_recovery_run_20261101/recovery_controller.py](feduba_mixed_attack_recovery_run_20261101/recovery_controller.py)
- [research/feduba_mixed_attack_recovery_run_20261101/recovery_io.py](feduba_mixed_attack_recovery_run_20261101/recovery_io.py)
- [research/feduba_mixed_attack_recovery_run_20261101/REPORT_KO.txt](feduba_mixed_attack_recovery_run_20261101/REPORT_KO.txt)
- [research/feduba_mixed_attack_recovery_run_20261101/resume_attack.py](feduba_mixed_attack_recovery_run_20261101/resume_attack.py)
- [research/feduba_mixed_attack_recovery_run_20261101/runtime_common.py](feduba_mixed_attack_recovery_run_20261101/runtime_common.py)
- [research/feduba_mixed_attack_recovery_run_20261101/SOURCE_CHECKS.json](feduba_mixed_attack_recovery_run_20261101/SOURCE_CHECKS.json)
- [research/feduba_mixed_attack_recovery_run_20261101/SOURCE_FREEZE.json](feduba_mixed_attack_recovery_run_20261101/SOURCE_FREEZE.json)
- [research/feduba_mixed_attack_recovery_run_20261101/SOURCE_PROFILE.json](feduba_mixed_attack_recovery_run_20261101/SOURCE_PROFILE.json)
- [research/feduba_mixed_attack_recovery_run_20261101/source_review.py](feduba_mixed_attack_recovery_run_20261101/source_review.py)
- [research/feduba_mixed_attack_recovery_run_20261101/trigger_binding.py](feduba_mixed_attack_recovery_run_20261101/trigger_binding.py)
- [research/feduba_mixed_attack_recovery_run_20261101/verify_fu.py](feduba_mixed_attack_recovery_run_20261101/verify_fu.py)
- [research/feduba_mixed_attack_recovery_run_20261101/verify_pair_evaluation.py](feduba_mixed_attack_recovery_run_20261101/verify_pair_evaluation.py)
- [research/feduba_mixed_attack_recovery_run_20261101/CASE_GUARD.json](feduba_mixed_attack_recovery_run_20261101/CASE_GUARD.json)
- [research/feduba_mixed_attack_recovery_run_20261101/DATA_CHECKS.json](feduba_mixed_attack_recovery_run_20261101/DATA_CHECKS.json)
- [research/feduba_mixed_attack_recovery_run_20261101/LAUNCH_PROFILE.json](feduba_mixed_attack_recovery_run_20261101/LAUNCH_PROFILE.json)
- [research/feduba_mixed_attack_recovery_run_20261101/PREPARATION_COPY_CHECKS.json](feduba_mixed_attack_recovery_run_20261101/PREPARATION_COPY_CHECKS.json)
- [research/feduba_mixed_attack_recovery_run_20261101/PREPARATION_TERMINAL.json](feduba_mixed_attack_recovery_run_20261101/PREPARATION_TERMINAL.json)
- [research/feduba_mixed_attack_recovery_run_20261101/PREPARE_ONCE.json](feduba_mixed_attack_recovery_run_20261101/PREPARE_ONCE.json)
- [research/feduba_mixed_attack_recovery_run_20261101/PREPARE_RESULT.json](feduba_mixed_attack_recovery_run_20261101/PREPARE_RESULT.json)
- [research/feduba_mixed_attack_recovery_run_20261101/PREPARE_TASK_ONCE.json](feduba_mixed_attack_recovery_run_20261101/PREPARE_TASK_ONCE.json)
- [research/feduba_mixed_attack_recovery_run_20261101/RECOVERY_INPUT_BINDING.json](feduba_mixed_attack_recovery_run_20261101/RECOVERY_INPUT_BINDING.json)
- [research/feduba_mixed_attack_recovery_run_20261101/RUN_FREEZE.json](feduba_mixed_attack_recovery_run_20261101/RUN_FREEZE.json)
- [research/feduba_mixed_attack_recovery_run_20261101/SOURCE_PUBLICATION.json](feduba_mixed_attack_recovery_run_20261101/SOURCE_PUBLICATION.json)
- [research/feduba_mixed_attack_recovery_run_20261101/SOURCE_REVIEW_ONCE.json](feduba_mixed_attack_recovery_run_20261101/SOURCE_REVIEW_ONCE.json)
- [research/feduba_mixed_attack_recovery_run_20261101/SOURCE_REVIEW_RESULT.json](feduba_mixed_attack_recovery_run_20261101/SOURCE_REVIEW_RESULT.json)
- [research/feduba_mixed_attack_recovery_run_20261101/TERMINAL_OBSERVATION.json](feduba_mixed_attack_recovery_run_20261101/TERMINAL_OBSERVATION.json)
- [research/feduba_mixed_attack_recovery_run_20261101/RECOVERY_ATTACK_ONCE.json](feduba_mixed_attack_recovery_run_20261101/RECOVERY_ATTACK_ONCE.json)
- [research/feduba_mixed_attack_recovery_run_20261101/RECOVERY_CONTROLLER_ONCE.json](feduba_mixed_attack_recovery_run_20261101/RECOVERY_CONTROLLER_ONCE.json)
- [research/feduba_mixed_attack_recovery_run_20261101/RECOVERY_TASK_ONCE.json](feduba_mixed_attack_recovery_run_20261101/RECOVERY_TASK_ONCE.json)
- [research/feduba_mixed_attack_recovery_run_20261101/RUN_PUBLICATION.json](feduba_mixed_attack_recovery_run_20261101/RUN_PUBLICATION.json)
- [research/feduba_mixed_attack_recovery_run_20261101/START_RECEIPT_COPY_CHECKS.json](feduba_mixed_attack_recovery_run_20261101/START_RECEIPT_COPY_CHECKS.json)
- [research/feduba_mixed_attack_recovery_run_20261101/STARTED_OBSERVATION.json](feduba_mixed_attack_recovery_run_20261101/STARTED_OBSERVATION.json)
- [research/feduba_mixed_attack_recovery_run_20261101/TRAIN_RUNTIME_OBSERVATION.json](feduba_mixed_attack_recovery_run_20261101/TRAIN_RUNTIME_OBSERVATION.json)
- [research/feduba_metric_conformance_review_20261101/REPORT_KO.txt](feduba_metric_conformance_review_20261101/REPORT_KO.txt)
- [research/feduba_metric_conformance_review_20261101/EVIDENCE.json](feduba_metric_conformance_review_20261101/EVIDENCE.json)
- [research/feduba_metric_conformance_review_20261101/STATUS_OBSERVATION.json](feduba_metric_conformance_review_20261101/STATUS_OBSERVATION.json)
- [research/feduba_mixed_attack_recovery_run_20261101/FU_attack_RESULT.json](feduba_mixed_attack_recovery_run_20261101/FU_attack_RESULT.json)
- [research/feduba_mixed_attack_recovery_run_20261101/ATTACK_TRAIN_COMPLETION_OBSERVATION.json](feduba_mixed_attack_recovery_run_20261101/ATTACK_TRAIN_COMPLETION_OBSERVATION.json)
- [research/feduba_mixed_attack_recovery_run_20261101/ATTACK_TRAIN_COMPLETION_SUMMARY.json](feduba_mixed_attack_recovery_run_20261101/ATTACK_TRAIN_COMPLETION_SUMMARY.json)
- [research/feduba_mixed_attack_recovery_run_20261101/FU_attack_VERIFIED.json](feduba_mixed_attack_recovery_run_20261101/FU_attack_VERIFIED.json)
- [research/feduba_mixed_attack_recovery_run_20261101/PAIR_EVAL_FAILURE.json](feduba_mixed_attack_recovery_run_20261101/PAIR_EVAL_FAILURE.json)
- [research/feduba_mixed_attack_recovery_run_20261101/RECOVERY_CONTROLLER_FAILURE.json](feduba_mixed_attack_recovery_run_20261101/RECOVERY_CONTROLLER_FAILURE.json)
- [research/feduba_mixed_attack_recovery_run_20261101/EVALUATION_GUARD_FAILURE_OBSERVATION.json](feduba_mixed_attack_recovery_run_20261101/EVALUATION_GUARD_FAILURE_OBSERVATION.json)
- [research/feduba_mixed_attack_recovery_run_20261101/EVALUATION_GUARD_FAILURE_TERMINAL.json](feduba_mixed_attack_recovery_run_20261101/EVALUATION_GUARD_FAILURE_TERMINAL.json)
- [research/feduba_mixed_attack_recovery_run_20261101/ATTACK_AUDIT_COMPLETION_SUMMARY.json](feduba_mixed_attack_recovery_run_20261101/ATTACK_AUDIT_COMPLETION_SUMMARY.json)
- [research/feduba_mixed_pair_evaluation_recovery_20261101/.gitattributes](feduba_mixed_pair_evaluation_recovery_20261101/.gitattributes)
- [research/feduba_mixed_pair_evaluation_recovery_20261101/.gitignore](feduba_mixed_pair_evaluation_recovery_20261101/.gitignore)
- [research/feduba_mixed_pair_evaluation_recovery_20261101/COPY_PROVENANCE.json](feduba_mixed_pair_evaluation_recovery_20261101/COPY_PROVENANCE.json)
- [research/feduba_mixed_pair_evaluation_recovery_20261101/evaluate_pair.py](feduba_mixed_pair_evaluation_recovery_20261101/evaluate_pair.py)
- [research/feduba_mixed_pair_evaluation_recovery_20261101/evaluation_controller.py](feduba_mixed_pair_evaluation_recovery_20261101/evaluation_controller.py)
- [research/feduba_mixed_pair_evaluation_recovery_20261101/evaluation_io.py](feduba_mixed_pair_evaluation_recovery_20261101/evaluation_io.py)
- [research/feduba_mixed_pair_evaluation_recovery_20261101/launch_evaluation.ps1](feduba_mixed_pair_evaluation_recovery_20261101/launch_evaluation.ps1)
- [research/feduba_mixed_pair_evaluation_recovery_20261101/LOCAL_SOURCE_CONSTRUCTION_INCIDENT.json](feduba_mixed_pair_evaluation_recovery_20261101/LOCAL_SOURCE_CONSTRUCTION_INCIDENT.json)
- [research/feduba_mixed_pair_evaluation_recovery_20261101/model_reference.py](feduba_mixed_pair_evaluation_recovery_20261101/model_reference.py)
- [research/feduba_mixed_pair_evaluation_recovery_20261101/MONITOR_PROTOCOL.txt](feduba_mixed_pair_evaluation_recovery_20261101/MONITOR_PROTOCOL.txt)
- [research/feduba_mixed_pair_evaluation_recovery_20261101/native_memory.py](feduba_mixed_pair_evaluation_recovery_20261101/native_memory.py)
- [research/feduba_mixed_pair_evaluation_recovery_20261101/native_processes.py](feduba_mixed_pair_evaluation_recovery_20261101/native_processes.py)
- [research/feduba_mixed_pair_evaluation_recovery_20261101/NUMERICAL_LOOP_REVIEW.json](feduba_mixed_pair_evaluation_recovery_20261101/NUMERICAL_LOOP_REVIEW.json)
- [research/feduba_mixed_pair_evaluation_recovery_20261101/observe_status.py](feduba_mixed_pair_evaluation_recovery_20261101/observe_status.py)
- [research/feduba_mixed_pair_evaluation_recovery_20261101/pair_binding.py](feduba_mixed_pair_evaluation_recovery_20261101/pair_binding.py)
- [research/feduba_mixed_pair_evaluation_recovery_20261101/pair_eval_core.py](feduba_mixed_pair_evaluation_recovery_20261101/pair_eval_core.py)
- [research/feduba_mixed_pair_evaluation_recovery_20261101/prepare_launch.py](feduba_mixed_pair_evaluation_recovery_20261101/prepare_launch.py)
- [research/feduba_mixed_pair_evaluation_recovery_20261101/PRIOR_EVALUATION_GUARD_FAILURE_TERMINAL.json](feduba_mixed_pair_evaluation_recovery_20261101/PRIOR_EVALUATION_GUARD_FAILURE_TERMINAL.json)
- [research/feduba_mixed_pair_evaluation_recovery_20261101/PRIOR_PAIR_EVAL_FAILURE.json](feduba_mixed_pair_evaluation_recovery_20261101/PRIOR_PAIR_EVAL_FAILURE.json)
- [research/feduba_mixed_pair_evaluation_recovery_20261101/PRIOR_RECOVERY_CONTROLLER_FAILURE.json](feduba_mixed_pair_evaluation_recovery_20261101/PRIOR_RECOVERY_CONTROLLER_FAILURE.json)
- [research/feduba_mixed_pair_evaluation_recovery_20261101/PROTOCOL.txt](feduba_mixed_pair_evaluation_recovery_20261101/PROTOCOL.txt)
- [research/feduba_mixed_pair_evaluation_recovery_20261101/QUERY_STATUS.ps1](feduba_mixed_pair_evaluation_recovery_20261101/QUERY_STATUS.ps1)
- [research/feduba_mixed_pair_evaluation_recovery_20261101/REPORT_KO.txt](feduba_mixed_pair_evaluation_recovery_20261101/REPORT_KO.txt)
- [research/feduba_mixed_pair_evaluation_recovery_20261101/runtime_common.py](feduba_mixed_pair_evaluation_recovery_20261101/runtime_common.py)
- [research/feduba_mixed_pair_evaluation_recovery_20261101/SOURCE_CHECKS.json](feduba_mixed_pair_evaluation_recovery_20261101/SOURCE_CHECKS.json)
- [research/feduba_mixed_pair_evaluation_recovery_20261101/SOURCE_FREEZE.json](feduba_mixed_pair_evaluation_recovery_20261101/SOURCE_FREEZE.json)
- [research/feduba_mixed_pair_evaluation_recovery_20261101/source_probe.py](feduba_mixed_pair_evaluation_recovery_20261101/source_probe.py)
- [research/feduba_mixed_pair_evaluation_recovery_20261101/SOURCE_PROFILE.json](feduba_mixed_pair_evaluation_recovery_20261101/SOURCE_PROFILE.json)
- [research/feduba_mixed_pair_evaluation_recovery_20261101/trigger_binding.py](feduba_mixed_pair_evaluation_recovery_20261101/trigger_binding.py)
- [research/feduba_mixed_pair_evaluation_recovery_20261101/verify_pair_evaluation.py](feduba_mixed_pair_evaluation_recovery_20261101/verify_pair_evaluation.py)
- [research/feduba_mixed_pair_evaluation_recovery_20261101/PUBLICATION_WHITESPACE_CHECK.json](feduba_mixed_pair_evaluation_recovery_20261101/PUBLICATION_WHITESPACE_CHECK.json)
- [research/feduba_mixed_pair_evaluation_recovery_20261101/SOURCE_PUBLICATION.json](feduba_mixed_pair_evaluation_recovery_20261101/SOURCE_PUBLICATION.json)
- [research/feduba_mixed_pair_evaluation_recovery_20261101/METADATA_PROBE_ONCE.json](feduba_mixed_pair_evaluation_recovery_20261101/METADATA_PROBE_ONCE.json)
- [research/feduba_mixed_pair_evaluation_recovery_20261101/METADATA_PROBE_RESULT.json](feduba_mixed_pair_evaluation_recovery_20261101/METADATA_PROBE_RESULT.json)
- [research/feduba_mixed_pair_evaluation_recovery_20261101/METADATA_PROBE_DONE.json](feduba_mixed_pair_evaluation_recovery_20261101/METADATA_PROBE_DONE.json)
- [research/feduba_mixed_pair_evaluation_recovery_20261101/METADATA_PROBE_CIM_MATCH.json](feduba_mixed_pair_evaluation_recovery_20261101/METADATA_PROBE_CIM_MATCH.json)
- [research/feduba_mixed_pair_evaluation_recovery_20261101/NATIVE_PEER_GUARD_SCOPE_FINDING.json](feduba_mixed_pair_evaluation_recovery_20261101/NATIVE_PEER_GUARD_SCOPE_FINDING.json)
- [research/feduba_mixed_pair_eval_native_v2_20261101/.gitattributes](feduba_mixed_pair_eval_native_v2_20261101/.gitattributes)
- [research/feduba_mixed_pair_eval_native_v2_20261101/.gitignore](feduba_mixed_pair_eval_native_v2_20261101/.gitignore)
- [research/feduba_mixed_pair_eval_native_v2_20261101/COPY_PROVENANCE.json](feduba_mixed_pair_eval_native_v2_20261101/COPY_PROVENANCE.json)
- [research/feduba_mixed_pair_eval_native_v2_20261101/evaluate_pair.py](feduba_mixed_pair_eval_native_v2_20261101/evaluate_pair.py)
- [research/feduba_mixed_pair_eval_native_v2_20261101/evaluation_controller.py](feduba_mixed_pair_eval_native_v2_20261101/evaluation_controller.py)
- [research/feduba_mixed_pair_eval_native_v2_20261101/evaluation_io.py](feduba_mixed_pair_eval_native_v2_20261101/evaluation_io.py)
- [research/feduba_mixed_pair_eval_native_v2_20261101/launch_evaluation.ps1](feduba_mixed_pair_eval_native_v2_20261101/launch_evaluation.ps1)
- [research/feduba_mixed_pair_eval_native_v2_20261101/launch_probe.ps1](feduba_mixed_pair_eval_native_v2_20261101/launch_probe.ps1)
- [research/feduba_mixed_pair_eval_native_v2_20261101/LOCAL_POWERSHELL_INVOCATION_FAILURE.json](feduba_mixed_pair_eval_native_v2_20261101/LOCAL_POWERSHELL_INVOCATION_FAILURE.json)
- [research/feduba_mixed_pair_eval_native_v2_20261101/LOCAL_SOURCE_CONSTRUCTION_INCIDENT.json](feduba_mixed_pair_eval_native_v2_20261101/LOCAL_SOURCE_CONSTRUCTION_INCIDENT.json)
- [research/feduba_mixed_pair_eval_native_v2_20261101/model_reference.py](feduba_mixed_pair_eval_native_v2_20261101/model_reference.py)
- [research/feduba_mixed_pair_eval_native_v2_20261101/MONITOR_PROTOCOL.txt](feduba_mixed_pair_eval_native_v2_20261101/MONITOR_PROTOCOL.txt)
- [research/feduba_mixed_pair_eval_native_v2_20261101/native_memory.py](feduba_mixed_pair_eval_native_v2_20261101/native_memory.py)
- [research/feduba_mixed_pair_eval_native_v2_20261101/native_processes.py](feduba_mixed_pair_eval_native_v2_20261101/native_processes.py)
- [research/feduba_mixed_pair_eval_native_v2_20261101/NUMERICAL_LOOP_REVIEW.json](feduba_mixed_pair_eval_native_v2_20261101/NUMERICAL_LOOP_REVIEW.json)
- [research/feduba_mixed_pair_eval_native_v2_20261101/observe_status.py](feduba_mixed_pair_eval_native_v2_20261101/observe_status.py)
- [research/feduba_mixed_pair_eval_native_v2_20261101/pair_binding.py](feduba_mixed_pair_eval_native_v2_20261101/pair_binding.py)
- [research/feduba_mixed_pair_eval_native_v2_20261101/pair_eval_core.py](feduba_mixed_pair_eval_native_v2_20261101/pair_eval_core.py)
- [research/feduba_mixed_pair_eval_native_v2_20261101/prepare_launch.py](feduba_mixed_pair_eval_native_v2_20261101/prepare_launch.py)
- [research/feduba_mixed_pair_eval_native_v2_20261101/PRIOR_EVALUATION_GUARD_FAILURE_TERMINAL.json](feduba_mixed_pair_eval_native_v2_20261101/PRIOR_EVALUATION_GUARD_FAILURE_TERMINAL.json)
- [research/feduba_mixed_pair_eval_native_v2_20261101/PRIOR_NATIVE_V1_METADATA_PROBE_CIM_MATCH.json](feduba_mixed_pair_eval_native_v2_20261101/PRIOR_NATIVE_V1_METADATA_PROBE_CIM_MATCH.json)
- [research/feduba_mixed_pair_eval_native_v2_20261101/PRIOR_NATIVE_V1_METADATA_PROBE_DONE.json](feduba_mixed_pair_eval_native_v2_20261101/PRIOR_NATIVE_V1_METADATA_PROBE_DONE.json)
- [research/feduba_mixed_pair_eval_native_v2_20261101/PRIOR_NATIVE_V1_METADATA_PROBE_RESULT.json](feduba_mixed_pair_eval_native_v2_20261101/PRIOR_NATIVE_V1_METADATA_PROBE_RESULT.json)
- [research/feduba_mixed_pair_eval_native_v2_20261101/PRIOR_NATIVE_V1_NATIVE_PEER_GUARD_SCOPE_FINDING.json](feduba_mixed_pair_eval_native_v2_20261101/PRIOR_NATIVE_V1_NATIVE_PEER_GUARD_SCOPE_FINDING.json)
- [research/feduba_mixed_pair_eval_native_v2_20261101/PRIOR_NATIVE_V1_SOURCE_FREEZE.json](feduba_mixed_pair_eval_native_v2_20261101/PRIOR_NATIVE_V1_SOURCE_FREEZE.json)
- [research/feduba_mixed_pair_eval_native_v2_20261101/PRIOR_NATIVE_V1_SOURCE_PUBLICATION.json](feduba_mixed_pair_eval_native_v2_20261101/PRIOR_NATIVE_V1_SOURCE_PUBLICATION.json)
- [research/feduba_mixed_pair_eval_native_v2_20261101/PRIOR_PAIR_EVAL_FAILURE.json](feduba_mixed_pair_eval_native_v2_20261101/PRIOR_PAIR_EVAL_FAILURE.json)
- [research/feduba_mixed_pair_eval_native_v2_20261101/PRIOR_RECOVERY_CONTROLLER_FAILURE.json](feduba_mixed_pair_eval_native_v2_20261101/PRIOR_RECOVERY_CONTROLLER_FAILURE.json)
- [research/feduba_mixed_pair_eval_native_v2_20261101/PROTOCOL.txt](feduba_mixed_pair_eval_native_v2_20261101/PROTOCOL.txt)
- [research/feduba_mixed_pair_eval_native_v2_20261101/QUERY_STATUS.ps1](feduba_mixed_pair_eval_native_v2_20261101/QUERY_STATUS.ps1)
- [research/feduba_mixed_pair_eval_native_v2_20261101/REPORT_KO.txt](feduba_mixed_pair_eval_native_v2_20261101/REPORT_KO.txt)
- [research/feduba_mixed_pair_eval_native_v2_20261101/runtime_common.py](feduba_mixed_pair_eval_native_v2_20261101/runtime_common.py)
- [research/feduba_mixed_pair_eval_native_v2_20261101/SOURCE_CHECKS.json](feduba_mixed_pair_eval_native_v2_20261101/SOURCE_CHECKS.json)
- [research/feduba_mixed_pair_eval_native_v2_20261101/SOURCE_FREEZE.json](feduba_mixed_pair_eval_native_v2_20261101/SOURCE_FREEZE.json)
- [research/feduba_mixed_pair_eval_native_v2_20261101/source_probe.py](feduba_mixed_pair_eval_native_v2_20261101/source_probe.py)
- [research/feduba_mixed_pair_eval_native_v2_20261101/SOURCE_PROFILE.json](feduba_mixed_pair_eval_native_v2_20261101/SOURCE_PROFILE.json)
- [research/feduba_mixed_pair_eval_native_v2_20261101/trigger_binding.py](feduba_mixed_pair_eval_native_v2_20261101/trigger_binding.py)
- [research/feduba_mixed_pair_eval_native_v2_20261101/verify_pair_evaluation.py](feduba_mixed_pair_eval_native_v2_20261101/verify_pair_evaluation.py)
- [research/feduba_mixed_pair_eval_native_v2_20261101/SOURCE_PUBLICATION.json](feduba_mixed_pair_eval_native_v2_20261101/SOURCE_PUBLICATION.json)
- [research/feduba_mixed_pair_eval_native_v2_20261101/METADATA_PROBE_TASK_ONCE.json](feduba_mixed_pair_eval_native_v2_20261101/METADATA_PROBE_TASK_ONCE.json)
- [research/feduba_mixed_pair_eval_native_v2_20261101/METADATA_PROBE_ONCE.json](feduba_mixed_pair_eval_native_v2_20261101/METADATA_PROBE_ONCE.json)
- [research/feduba_mixed_pair_eval_native_v2_20261101/METADATA_PROBE_RESULT.json](feduba_mixed_pair_eval_native_v2_20261101/METADATA_PROBE_RESULT.json)
- [research/feduba_mixed_pair_eval_native_v2_20261101/METADATA_PROBE_DONE.json](feduba_mixed_pair_eval_native_v2_20261101/METADATA_PROBE_DONE.json)
- [research/feduba_mixed_pair_eval_native_v2_20261101/METADATA_PROBE_CIM_MATCH.json](feduba_mixed_pair_eval_native_v2_20261101/METADATA_PROBE_CIM_MATCH.json)
- [research/feduba_mixed_pair_eval_native_v2_20261101/METADATA_PROBE_TERMINAL.json](feduba_mixed_pair_eval_native_v2_20261101/METADATA_PROBE_TERMINAL.json)
- [research/feduba_mixed_pair_eval_native_v2_20261101/EARLY_TERMINAL_READ_OBSERVATION.json](feduba_mixed_pair_eval_native_v2_20261101/EARLY_TERMINAL_READ_OBSERVATION.json)
- [research/feduba_mixed_pair_eval_native_v2_20261101/PREPARE_ONCE.json](feduba_mixed_pair_eval_native_v2_20261101/PREPARE_ONCE.json)
- [research/feduba_mixed_pair_eval_native_v2_20261101/PREPARE_RESULT.json](feduba_mixed_pair_eval_native_v2_20261101/PREPARE_RESULT.json)
- [research/feduba_mixed_pair_eval_native_v2_20261101/CASE_GUARD.json](feduba_mixed_pair_eval_native_v2_20261101/CASE_GUARD.json)
- [research/feduba_mixed_pair_eval_native_v2_20261101/EVALUATION_INPUT_BINDING.json](feduba_mixed_pair_eval_native_v2_20261101/EVALUATION_INPUT_BINDING.json)
- [research/feduba_mixed_pair_eval_native_v2_20261101/LAUNCH_PROFILE.json](feduba_mixed_pair_eval_native_v2_20261101/LAUNCH_PROFILE.json)
- [research/feduba_mixed_pair_eval_native_v2_20261101/RUN_FREEZE.json](feduba_mixed_pair_eval_native_v2_20261101/RUN_FREEZE.json)
- [research/feduba_mixed_pair_eval_native_v2_20261101/PREPARATION_COPY_CHECKS.json](feduba_mixed_pair_eval_native_v2_20261101/PREPARATION_COPY_CHECKS.json)
- [research/feduba_mixed_pair_eval_native_v2_20261101/RUN_PUBLICATION.json](feduba_mixed_pair_eval_native_v2_20261101/RUN_PUBLICATION.json)
- [research/feduba_mixed_pair_eval_native_v2_20261101/EVALUATION_TASK_ONCE.json](feduba_mixed_pair_eval_native_v2_20261101/EVALUATION_TASK_ONCE.json)
- [research/feduba_mixed_pair_eval_native_v2_20261101/EVALUATION_CONTROLLER_ONCE.json](feduba_mixed_pair_eval_native_v2_20261101/EVALUATION_CONTROLLER_ONCE.json)
- [research/feduba_mixed_pair_eval_native_v2_20261101/PAIR_EVAL_ONCE.json](feduba_mixed_pair_eval_native_v2_20261101/PAIR_EVAL_ONCE.json)
- [research/feduba_mixed_pair_eval_native_v2_20261101/PAIR_EVAL_AUDIT_ONCE.json](feduba_mixed_pair_eval_native_v2_20261101/PAIR_EVAL_AUDIT_ONCE.json)
- [research/feduba_mixed_pair_eval_native_v2_20261101/PAIR_EVAL_RESULT.json](feduba_mixed_pair_eval_native_v2_20261101/PAIR_EVAL_RESULT.json)
- [research/feduba_mixed_pair_eval_native_v2_20261101/PAIR_EVAL_VERIFIED.json](feduba_mixed_pair_eval_native_v2_20261101/PAIR_EVAL_VERIFIED.json)
- [research/feduba_mixed_pair_eval_native_v2_20261101/COMPLETION.json](feduba_mixed_pair_eval_native_v2_20261101/COMPLETION.json)
- [research/feduba_mixed_pair_eval_native_v2_20261101/EVALUATION_COMPLETION_COPY_CHECKS.json](feduba_mixed_pair_eval_native_v2_20261101/EVALUATION_COMPLETION_COPY_CHECKS.json)
- [research/feduba_mixed_pair_eval_native_v2_20261101/EVALUATION_COMPLETION_SUMMARY.json](feduba_mixed_pair_eval_native_v2_20261101/EVALUATION_COMPLETION_SUMMARY.json)
- [research/feduba_mixed_pair_eval_native_v2_20261101/PAPER_COMPARISON.txt](feduba_mixed_pair_eval_native_v2_20261101/PAPER_COMPARISON.txt)
- [research/feduba_mixed_pair_eval_native_v2_20261101/COMPLETION_REPORT_KO.txt](feduba_mixed_pair_eval_native_v2_20261101/COMPLETION_REPORT_KO.txt)
- [research/feduba_mixed_pair_delivery_20261101/PROTOCOL.txt](feduba_mixed_pair_delivery_20261101/PROTOCOL.txt)
- [research/feduba_mixed_pair_delivery_20261101/DESIGN_INPUT_STATE.json](feduba_mixed_pair_delivery_20261101/DESIGN_INPUT_STATE.json)
- [research/feduba_mixed_pair_delivery_20261101/REPORT_KO.txt](feduba_mixed_pair_delivery_20261101/REPORT_KO.txt)
- [research/feduba_mixed_pair_delivery_20261101/ACTUAL_SOURCE_FREEZE_CHECKS.json](feduba_mixed_pair_delivery_20261101/ACTUAL_SOURCE_FREEZE_CHECKS.json)
- [research/feduba_mixed_pair_delivery_20261101/COPY_PROVENANCE.json](feduba_mixed_pair_delivery_20261101/COPY_PROVENANCE.json)
- [research/feduba_mixed_pair_delivery_20261101/DELIVERY_PROFILE.json](feduba_mixed_pair_delivery_20261101/DELIVERY_PROFILE.json)
- [research/feduba_mixed_pair_delivery_20261101/EXECUTION_CONTRACT.txt](feduba_mixed_pair_delivery_20261101/EXECUTION_CONTRACT.txt)
- [research/feduba_mixed_pair_delivery_20261101/export_mixed_pair.py](feduba_mixed_pair_delivery_20261101/export_mixed_pair.py)
- [research/feduba_mixed_pair_delivery_20261101/launch_export.ps1](feduba_mixed_pair_delivery_20261101/launch_export.ps1)
- [research/feduba_mixed_pair_delivery_20261101/model_reference.py](feduba_mixed_pair_delivery_20261101/model_reference.py)
- [research/feduba_mixed_pair_delivery_20261101/native_memory.py](feduba_mixed_pair_delivery_20261101/native_memory.py)
- [research/feduba_mixed_pair_delivery_20261101/native_processes.py](feduba_mixed_pair_delivery_20261101/native_processes.py)
- [research/feduba_mixed_pair_delivery_20261101/pair_review_common.py](feduba_mixed_pair_delivery_20261101/pair_review_common.py)
- [research/feduba_mixed_pair_delivery_20261101/receive_pair_review.py](feduba_mixed_pair_delivery_20261101/receive_pair_review.py)
- [research/feduba_mixed_pair_delivery_20261101/register_pair_cases.py](feduba_mixed_pair_delivery_20261101/register_pair_cases.py)
- [research/feduba_mixed_pair_delivery_20261101/SOURCE_FREEZE.json](feduba_mixed_pair_delivery_20261101/SOURCE_FREEZE.json)
- [research/feduba_mixed_pair_delivery_20261101/source_review.py](feduba_mixed_pair_delivery_20261101/source_review.py)
- [research/feduba_mixed_pair_delivery_20261101/SOURCE_REVIEW_ONCE.json](feduba_mixed_pair_delivery_20261101/SOURCE_REVIEW_ONCE.json)
- [research/feduba_mixed_pair_delivery_20261101/SOURCE_REVIEW_RESULT.json](feduba_mixed_pair_delivery_20261101/SOURCE_REVIEW_RESULT.json)
- [research/feduba_mixed_pair_delivery_20261101/DELIVERY_PUBLICATION.json](feduba_mixed_pair_delivery_20261101/DELIVERY_PUBLICATION.json)
- [research/feduba_mixed_pair_delivery_20261101/PAIR_REVIEW_TASK_ONCE.json](feduba_mixed_pair_delivery_20261101/PAIR_REVIEW_TASK_ONCE.json)
- [research/feduba_mixed_pair_delivery_20261101/PAIR_REVIEW_EXPORT_ONCE.json](feduba_mixed_pair_delivery_20261101/PAIR_REVIEW_EXPORT_ONCE.json)
- [research/feduba_mixed_pair_delivery_20261101/PAIR_REVIEW_DELIVERY_REMOTE.json](feduba_mixed_pair_delivery_20261101/PAIR_REVIEW_DELIVERY_REMOTE.json)
- [research/feduba_mixed_pair_delivery_20261101/ARCHIVE_TRANSFER_CHECKS.json](feduba_mixed_pair_delivery_20261101/ARCHIVE_TRANSFER_CHECKS.json)
- [research/feduba_mixed_pair_delivery_20261101/observe_delivery_status.py](feduba_mixed_pair_delivery_20261101/observe_delivery_status.py)
- [research/feduba_mixed_pair_delivery_20261101/observe_local_receive.py](feduba_mixed_pair_delivery_20261101/observe_local_receive.py)
- [research/feduba_mixed_pair_delivery_20261101/MONITOR_PROTOCOL.txt](feduba_mixed_pair_delivery_20261101/MONITOR_PROTOCOL.txt)
- [research/feduba_mixed_pair_delivery_20261101/MONITOR_FREEZE.json](feduba_mixed_pair_delivery_20261101/MONITOR_FREEZE.json)
- [research/feduba_mixed_pair_delivery_20261101/LOCAL_RECEIVE_RESOURCE_OBSERVATION.json](feduba_mixed_pair_delivery_20261101/LOCAL_RECEIVE_RESOURCE_OBSERVATION.json)
- [research/feduba_mixed_pair_delivery_20261101/REMOTE_EXPORT_TERMINAL_CHECKS.json](feduba_mixed_pair_delivery_20261101/REMOTE_EXPORT_TERMINAL_CHECKS.json)
- [research/feduba_mixed_pair_delivery_20261101/DELIVERY_PROGRESS.json](feduba_mixed_pair_delivery_20261101/DELIVERY_PROGRESS.json)
- [research/feduba_mixed_pair_delivery_20261101/LOCAL_RECEIVE_INTERRUPTION_OBSERVATION_20261102.json](feduba_mixed_pair_delivery_20261101/LOCAL_RECEIVE_INTERRUPTION_OBSERVATION_20261102.json)
- [research/feduba_mixed_pair_delivery_20261101/LOCAL_RECEIVE_INTERRUPTION_REPORT_KO_20261102.txt](feduba_mixed_pair_delivery_20261101/LOCAL_RECEIVE_INTERRUPTION_REPORT_KO_20261102.txt)
- [research/feduba_mixed_pair_receive_recovery_20261102/.gitignore](feduba_mixed_pair_receive_recovery_20261102/.gitignore)
- [research/feduba_mixed_pair_receive_recovery_20261102/COPY_PROVENANCE.json](feduba_mixed_pair_receive_recovery_20261102/COPY_PROVENANCE.json)
- [research/feduba_mixed_pair_receive_recovery_20261102/PROTOCOL.txt](feduba_mixed_pair_receive_recovery_20261102/PROTOCOL.txt)
- [research/feduba_mixed_pair_receive_recovery_20261102/RECEIVE_PROFILE.json](feduba_mixed_pair_receive_recovery_20261102/RECEIVE_PROFILE.json)
- [research/feduba_mixed_pair_receive_recovery_20261102/REMOTE_METADATA_PREFLIGHT.json](feduba_mixed_pair_receive_recovery_20261102/REMOTE_METADATA_PREFLIGHT.json)
- [research/feduba_mixed_pair_receive_recovery_20261102/REPORT_KO.txt](feduba_mixed_pair_receive_recovery_20261102/REPORT_KO.txt)
- [research/feduba_mixed_pair_receive_recovery_20261102/SOURCE_FREEZE.json](feduba_mixed_pair_receive_recovery_20261102/SOURCE_FREEZE.json)
- [research/feduba_mixed_pair_receive_recovery_20261102/SOURCE_REVIEW_RESULT.json](feduba_mixed_pair_receive_recovery_20261102/SOURCE_REVIEW_RESULT.json)
- [research/feduba_mixed_pair_receive_recovery_20261102/launch_receive_once.py](feduba_mixed_pair_receive_recovery_20261102/launch_receive_once.py)
- [research/feduba_mixed_pair_receive_recovery_20261102/observe_receive.py](feduba_mixed_pair_receive_recovery_20261102/observe_receive.py)
- [research/feduba_mixed_pair_receive_recovery_20261102/receive_ops.py](feduba_mixed_pair_receive_recovery_20261102/receive_ops.py)
- [research/feduba_mixed_pair_receive_recovery_20261102/receive_recovery.py](feduba_mixed_pair_receive_recovery_20261102/receive_recovery.py)
- [research/feduba_mixed_pair_receive_recovery_20261102/receive_task.xml](feduba_mixed_pair_receive_recovery_20261102/receive_task.xml)
- [research/feduba_mixed_pair_receive_recovery_20261102/source_checks.py](feduba_mixed_pair_receive_recovery_20261102/source_checks.py)
- [research/feduba_mixed_pair_receive_recovery_v2_20261102/.gitignore](feduba_mixed_pair_receive_recovery_v2_20261102/.gitignore)
- [research/feduba_mixed_pair_receive_recovery_v2_20261102/COPY_PROVENANCE.json](feduba_mixed_pair_receive_recovery_v2_20261102/COPY_PROVENANCE.json)
- [research/feduba_mixed_pair_receive_recovery_v2_20261102/PROTOCOL.txt](feduba_mixed_pair_receive_recovery_v2_20261102/PROTOCOL.txt)
- [research/feduba_mixed_pair_receive_recovery_v2_20261102/RECEIVE_PROFILE.json](feduba_mixed_pair_receive_recovery_v2_20261102/RECEIVE_PROFILE.json)
- [research/feduba_mixed_pair_receive_recovery_v2_20261102/REPORT_KO.txt](feduba_mixed_pair_receive_recovery_v2_20261102/REPORT_KO.txt)
- [research/feduba_mixed_pair_receive_recovery_v2_20261102/SOURCE_FREEZE.json](feduba_mixed_pair_receive_recovery_v2_20261102/SOURCE_FREEZE.json)
- [research/feduba_mixed_pair_receive_recovery_v2_20261102/SOURCE_REVIEW_RESULT.json](feduba_mixed_pair_receive_recovery_v2_20261102/SOURCE_REVIEW_RESULT.json)
- [research/feduba_mixed_pair_receive_recovery_v2_20261102/TASK_XML_VIEW.txt](feduba_mixed_pair_receive_recovery_v2_20261102/TASK_XML_VIEW.txt)
- [research/feduba_mixed_pair_receive_recovery_v2_20261102/launch_receive_once.py](feduba_mixed_pair_receive_recovery_v2_20261102/launch_receive_once.py)
- [research/feduba_mixed_pair_receive_recovery_v2_20261102/observe_receive.py](feduba_mixed_pair_receive_recovery_v2_20261102/observe_receive.py)
- [research/feduba_mixed_pair_receive_recovery_v2_20261102/receive_ops.py](feduba_mixed_pair_receive_recovery_v2_20261102/receive_ops.py)
- [research/feduba_mixed_pair_receive_recovery_v2_20261102/receive_recovery.py](feduba_mixed_pair_receive_recovery_v2_20261102/receive_recovery.py)
- [research/feduba_mixed_pair_receive_recovery_v2_20261102/receive_task.xml](feduba_mixed_pair_receive_recovery_v2_20261102/receive_task.xml)
- [research/feduba_mixed_pair_receive_recovery_v2_20261102/source_checks.py](feduba_mixed_pair_receive_recovery_v2_20261102/source_checks.py)
- [research/feduba_mixed_pair_receive_recovery_20261102/RECEIVE_PUBLICATION.json](feduba_mixed_pair_receive_recovery_20261102/RECEIVE_PUBLICATION.json)
- [research/feduba_mixed_pair_receive_recovery_20261102/TASK_ONCE.json](feduba_mixed_pair_receive_recovery_20261102/TASK_ONCE.json)
- [research/feduba_mixed_pair_receive_recovery_20261102/LAUNCH_FAILURE.json](feduba_mixed_pair_receive_recovery_20261102/LAUNCH_FAILURE.json)
- [research/feduba_mixed_pair_receive_recovery_20261102/LAUNCH_TERMINAL_OBSERVATION.json](feduba_mixed_pair_receive_recovery_20261102/LAUNCH_TERMINAL_OBSERVATION.json)
- [research/feduba_mixed_pair_receive_recovery_20261102/METADATA_MONITOR_IMPORT_FAILURE.json](feduba_mixed_pair_receive_recovery_20261102/METADATA_MONITOR_IMPORT_FAILURE.json)
- [research/feduba_mixed_pair_receive_start_20261102/.gitignore](feduba_mixed_pair_receive_start_20261102/.gitignore)
- [research/feduba_mixed_pair_receive_start_20261102/PROTOCOL.txt](feduba_mixed_pair_receive_start_20261102/PROTOCOL.txt)
- [research/feduba_mixed_pair_receive_start_20261102/REPORT_KO.txt](feduba_mixed_pair_receive_start_20261102/REPORT_KO.txt)
- [research/feduba_mixed_pair_receive_start_20261102/SOURCE_FREEZE.json](feduba_mixed_pair_receive_start_20261102/SOURCE_FREEZE.json)
- [research/feduba_mixed_pair_receive_start_20261102/SOURCE_REVIEW_RESULT.json](feduba_mixed_pair_receive_start_20261102/SOURCE_REVIEW_RESULT.json)
- [research/feduba_mixed_pair_receive_start_20261102/START_PROFILE.json](feduba_mixed_pair_receive_start_20261102/START_PROFILE.json)
- [research/feduba_mixed_pair_receive_start_20261102/observe_start.py](feduba_mixed_pair_receive_start_20261102/observe_start.py)
- [research/feduba_mixed_pair_receive_start_20261102/read_task.js](feduba_mixed_pair_receive_start_20261102/read_task.js)
- [research/feduba_mixed_pair_receive_start_20261102/source_checks.py](feduba_mixed_pair_receive_start_20261102/source_checks.py)
- [research/feduba_mixed_pair_receive_start_20261102/start_ops.py](feduba_mixed_pair_receive_start_20261102/start_ops.py)
- [research/feduba_mixed_pair_receive_start_20261102/start_registered_once.py](feduba_mixed_pair_receive_start_20261102/start_registered_once.py)
- [research/feduba_mixed_pair_receive_recovery_v2_20261102/RECEIVE_PUBLICATION.json](feduba_mixed_pair_receive_recovery_v2_20261102/RECEIVE_PUBLICATION.json)
- [research/feduba_mixed_pair_receive_recovery_v2_20261102/TASK_ONCE.json](feduba_mixed_pair_receive_recovery_v2_20261102/TASK_ONCE.json)
- [research/feduba_mixed_pair_receive_recovery_v2_20261102/LAUNCH_FAILURE.json](feduba_mixed_pair_receive_recovery_v2_20261102/LAUNCH_FAILURE.json)
- [research/feduba_mixed_pair_receive_recovery_v2_20261102/LAUNCH_TERMINAL_OBSERVATION.json](feduba_mixed_pair_receive_recovery_v2_20261102/LAUNCH_TERMINAL_OBSERVATION.json)
- [research/feduba_mixed_pair_receive_start_20261102/START_PUBLICATION.json](feduba_mixed_pair_receive_start_20261102/START_PUBLICATION.json)
- [research/feduba_mixed_pair_receive_start_20261102/START_ONCE.json](feduba_mixed_pair_receive_start_20261102/START_ONCE.json)
- [research/feduba_mixed_pair_receive_start_20261102/START_TERMINAL.json](feduba_mixed_pair_receive_start_20261102/START_TERMINAL.json)
- [research/feduba_mixed_pair_receive_start_20261102/RECEIVE_RUNNING_OBSERVATION.json](feduba_mixed_pair_receive_start_20261102/RECEIVE_RUNNING_OBSERVATION.json)
- [research/feduba_mixed_pair_receive_start_20261102/GUARD_WAIT_DURABILITY_CHECK.json](feduba_mixed_pair_receive_start_20261102/GUARD_WAIT_DURABILITY_CHECK.json)
- [research/feduba_mixed_pair_receive_recovery_v2_20261102/RECEIVE_ONCE.json](feduba_mixed_pair_receive_recovery_v2_20261102/RECEIVE_ONCE.json)
- [research/feduba_mixed_pair_receive_recovery_v2_20261102/ACTUAL_PROCESS.json](feduba_mixed_pair_receive_recovery_v2_20261102/ACTUAL_PROCESS.json)
- [research/feduba_mixed_pair_receive_recovery_v2_20261102/RESOURCE_WAIT_BEGIN.json](feduba_mixed_pair_receive_recovery_v2_20261102/RESOURCE_WAIT_BEGIN.json)
- [research/feduba_mixed_pair_receive_start_20261102/preserve_receiver_interruption_20261102.py](feduba_mixed_pair_receive_start_20261102/preserve_receiver_interruption_20261102.py)
- [research/feduba_mixed_pair_receive_start_20261102/RECEIVER_INTERRUPTION_OBSERVATION_20261102.json](feduba_mixed_pair_receive_start_20261102/RECEIVER_INTERRUPTION_OBSERVATION_20261102.json)
- [research/feduba_mixed_pair_receive_start_20261102/RESTART_WINDOW_EVIDENCE_20261102.json](feduba_mixed_pair_receive_start_20261102/RESTART_WINDOW_EVIDENCE_20261102.json)
- [research/feduba_mixed_pair_receive_start_20261102/REMOTE_AFTER_RECEIVER_INTERRUPTION_METADATA.json](feduba_mixed_pair_receive_start_20261102/REMOTE_AFTER_RECEIVER_INTERRUPTION_METADATA.json)
- [research/feduba_mixed_pair_receive_start_20261102/INTERRUPTION_PRESERVATION_CHECKS_20261102.json](feduba_mixed_pair_receive_start_20261102/INTERRUPTION_PRESERVATION_CHECKS_20261102.json)
- [research/feduba_mixed_pair_receive_start_20261102/RECEIVER_INTERRUPTION_REPORT_KO_20261102.txt](feduba_mixed_pair_receive_start_20261102/RECEIVER_INTERRUPTION_REPORT_KO_20261102.txt)
- [research/feduba_mixed_pair_receive_start_20261102/INTERRUPTION_METADATA_PROTOCOL.txt](feduba_mixed_pair_receive_start_20261102/INTERRUPTION_METADATA_PROTOCOL.txt)
- [research/feduba_mixed_pair_receive_start_20261102/INTERRUPTION_METADATA_FREEZE.json](feduba_mixed_pair_receive_start_20261102/INTERRUPTION_METADATA_FREEZE.json)
- [research/feduba_stg_conformance_review_20261102/.gitignore](feduba_stg_conformance_review_20261102/.gitignore)
- [research/feduba_stg_conformance_review_20261102/PROTOCOL.txt](feduba_stg_conformance_review_20261102/PROTOCOL.txt)
- [research/feduba_stg_conformance_review_20261102/review_saved_sources.py](feduba_stg_conformance_review_20261102/review_saved_sources.py)
- [research/feduba_stg_conformance_review_20261102/EVIDENCE.json](feduba_stg_conformance_review_20261102/EVIDENCE.json)
- [research/feduba_stg_conformance_review_20261102/REPORT_KO.txt](feduba_stg_conformance_review_20261102/REPORT_KO.txt)
- [research/feduba_stg_conformance_review_20261102/REVIEW_PROFILE.json](feduba_stg_conformance_review_20261102/REVIEW_PROFILE.json)
- [research/feduba_stg_conformance_review_20261102/REVIEW_FREEZE.json](feduba_stg_conformance_review_20261102/REVIEW_FREEZE.json)
- [research/feduba_public_stg_comparison_20261102/comparison_controller.py](feduba_public_stg_comparison_20261102/comparison_controller.py)
- [research/feduba_public_stg_comparison_20261102/DETACHED_LAUNCH_OBSERVATION.json](feduba_public_stg_comparison_20261102/DETACHED_LAUNCH_OBSERVATION.json)
- [research/feduba_public_stg_comparison_20261102/io_guard.py](feduba_public_stg_comparison_20261102/io_guard.py)
- [research/feduba_public_stg_comparison_20261102/launch_foreground.py](feduba_public_stg_comparison_20261102/launch_foreground.py)
- [research/feduba_public_stg_comparison_20261102/LAUNCH_RECOVERY_FREEZE.json](feduba_public_stg_comparison_20261102/LAUNCH_RECOVERY_FREEZE.json)
- [research/feduba_public_stg_comparison_20261102/LAUNCH_RECOVERY_PROFILE.json](feduba_public_stg_comparison_20261102/LAUNCH_RECOVERY_PROFILE.json)
- [research/feduba_public_stg_comparison_20261102/LAUNCH_RECOVERY_PROTOCOL.txt](feduba_public_stg_comparison_20261102/LAUNCH_RECOVERY_PROTOCOL.txt)
- [research/feduba_public_stg_comparison_20261102/LAUNCH_RECOVERY_PUBLICATION.json](feduba_public_stg_comparison_20261102/LAUNCH_RECOVERY_PUBLICATION.json)
- [research/feduba_public_stg_comparison_20261102/LAUNCH_REPORT_KO.txt](feduba_public_stg_comparison_20261102/LAUNCH_REPORT_KO.txt)
- [research/feduba_public_stg_comparison_20261102/native_memory.py](feduba_public_stg_comparison_20261102/native_memory.py)
- [research/feduba_public_stg_comparison_20261102/native_processes.py](feduba_public_stg_comparison_20261102/native_processes.py)
- [research/feduba_public_stg_comparison_20261102/PREPUBLICATION_COMMAND_OBSERVATION.json](feduba_public_stg_comparison_20261102/PREPUBLICATION_COMMAND_OBSERVATION.json)
- [research/feduba_public_stg_comparison_20261102/PROFILE.json](feduba_public_stg_comparison_20261102/PROFILE.json)
- [research/feduba_public_stg_comparison_20261102/PROTOCOL.txt](feduba_public_stg_comparison_20261102/PROTOCOL.txt)
- [research/feduba_public_stg_comparison_20261102/PUBLICATION.json](feduba_public_stg_comparison_20261102/PUBLICATION.json)
- [research/feduba_public_stg_comparison_20261102/public_stage.py](feduba_public_stg_comparison_20261102/public_stage.py)
- [research/feduba_public_stg_comparison_20261102/RUNNING_OBSERVATION.json](feduba_public_stg_comparison_20261102/RUNNING_OBSERVATION.json)
- [research/feduba_public_stg_comparison_20261102/run_comparison.py](feduba_public_stg_comparison_20261102/run_comparison.py)
- [research/feduba_public_stg_comparison_20261102/SOURCE_FREEZE.json](feduba_public_stg_comparison_20261102/SOURCE_FREEZE.json)
- [research/feduba_public_stg_comparison_20261102/source_review.py](feduba_public_stg_comparison_20261102/source_review.py)
- [research/feduba_public_stg_comparison_20261102/SOURCE_REVIEW_RESULT.json](feduba_public_stg_comparison_20261102/SOURCE_REVIEW_RESULT.json)
- [research/feduba_public_stg_comparison_20261102/verify_comparison.py](feduba_public_stg_comparison_20261102/verify_comparison.py)
- [research/feduba_public_stg_comparison_20261102/AUDIT_ONCE.json](feduba_public_stg_comparison_20261102/AUDIT_ONCE.json)
- [research/feduba_public_stg_comparison_20261102/COMPARISON_SUMMARY.json](feduba_public_stg_comparison_20261102/COMPARISON_SUMMARY.json)
- [research/feduba_public_stg_comparison_20261102/COMPLETION.json](feduba_public_stg_comparison_20261102/COMPLETION.json)
- [research/feduba_public_stg_comparison_20261102/COMPLETION_REPORT_KO.txt](feduba_public_stg_comparison_20261102/COMPLETION_REPORT_KO.txt)
- [research/feduba_public_stg_comparison_20261102/CONTROLLER_ONCE.json](feduba_public_stg_comparison_20261102/CONTROLLER_ONCE.json)
- [research/feduba_public_stg_comparison_20261102/CONTROLLER_STATE.json](feduba_public_stg_comparison_20261102/CONTROLLER_STATE.json)
- [research/feduba_public_stg_comparison_20261102/FOREGROUND_LAUNCH_ONCE.json](feduba_public_stg_comparison_20261102/FOREGROUND_LAUNCH_ONCE.json)
- [research/feduba_public_stg_comparison_20261102/LAUNCH_ONCE.json](feduba_public_stg_comparison_20261102/LAUNCH_ONCE.json)
- [research/feduba_public_stg_comparison_20261102/MANIFEST.json](feduba_public_stg_comparison_20261102/MANIFEST.json)
- [research/feduba_public_stg_comparison_20261102/NORMAL_CASE_SELECTION.json](feduba_public_stg_comparison_20261102/NORMAL_CASE_SELECTION.json)
- [research/feduba_public_stg_comparison_20261102/RELATED_HELPER_REFERENCE.json](feduba_public_stg_comparison_20261102/RELATED_HELPER_REFERENCE.json)
- [research/feduba_public_stg_comparison_20261102/RESULT.json](feduba_public_stg_comparison_20261102/RESULT.json)
- [research/feduba_public_stg_comparison_20261102/RUN_ONCE.json](feduba_public_stg_comparison_20261102/RUN_ONCE.json)
- [research/feduba_public_stg_comparison_20261102/TERMINAL_OBSERVATION.json](feduba_public_stg_comparison_20261102/TERMINAL_OBSERVATION.json)
- [research/feduba_public_stg_comparison_20261102/VERIFIED.json](feduba_public_stg_comparison_20261102/VERIFIED.json)
- [research/feduba_semantic_transfer_diagnosis_20261102/controller.py](feduba_semantic_transfer_diagnosis_20261102/controller.py)
- [research/feduba_semantic_transfer_diagnosis_20261102/io_guard.py](feduba_semantic_transfer_diagnosis_20261102/io_guard.py)
- [research/feduba_semantic_transfer_diagnosis_20261102/launch_foreground.py](feduba_semantic_transfer_diagnosis_20261102/launch_foreground.py)
- [research/feduba_semantic_transfer_diagnosis_20261102/native_memory.py](feduba_semantic_transfer_diagnosis_20261102/native_memory.py)
- [research/feduba_semantic_transfer_diagnosis_20261102/native_processes.py](feduba_semantic_transfer_diagnosis_20261102/native_processes.py)
- [research/feduba_semantic_transfer_diagnosis_20261102/PROFILE.json](feduba_semantic_transfer_diagnosis_20261102/PROFILE.json)
- [research/feduba_semantic_transfer_diagnosis_20261102/PROTOCOL.txt](feduba_semantic_transfer_diagnosis_20261102/PROTOCOL.txt)
- [research/feduba_semantic_transfer_diagnosis_20261102/semantic_diagnosis.py](feduba_semantic_transfer_diagnosis_20261102/semantic_diagnosis.py)
- [research/feduba_semantic_transfer_diagnosis_20261102/SOURCE_FREEZE.json](feduba_semantic_transfer_diagnosis_20261102/SOURCE_FREEZE.json)
- [research/feduba_semantic_transfer_diagnosis_20261102/source_review.py](feduba_semantic_transfer_diagnosis_20261102/source_review.py)
- [research/feduba_semantic_transfer_diagnosis_20261102/SOURCE_REVIEW_RESULT.json](feduba_semantic_transfer_diagnosis_20261102/SOURCE_REVIEW_RESULT.json)
- [research/feduba_semantic_transfer_diagnosis_20261102/TRANSPORT_FREEZE.json](feduba_semantic_transfer_diagnosis_20261102/TRANSPORT_FREEZE.json)
- [research/feduba_semantic_transfer_diagnosis_20261102/AUDIT_ONCE.json](feduba_semantic_transfer_diagnosis_20261102/AUDIT_ONCE.json)
- [research/feduba_semantic_transfer_diagnosis_20261102/CASE_SELECTION.json](feduba_semantic_transfer_diagnosis_20261102/CASE_SELECTION.json)
- [research/feduba_semantic_transfer_diagnosis_20261102/COMPLETION.json](feduba_semantic_transfer_diagnosis_20261102/COMPLETION.json)
- [research/feduba_semantic_transfer_diagnosis_20261102/COMPLETION_REPORT_KO.txt](feduba_semantic_transfer_diagnosis_20261102/COMPLETION_REPORT_KO.txt)
- [research/feduba_semantic_transfer_diagnosis_20261102/CONTROLLER_ONCE.json](feduba_semantic_transfer_diagnosis_20261102/CONTROLLER_ONCE.json)
- [research/feduba_semantic_transfer_diagnosis_20261102/CONTROLLER_STATE.json](feduba_semantic_transfer_diagnosis_20261102/CONTROLLER_STATE.json)
- [research/feduba_semantic_transfer_diagnosis_20261102/LAUNCH_ONCE.json](feduba_semantic_transfer_diagnosis_20261102/LAUNCH_ONCE.json)
- [research/feduba_semantic_transfer_diagnosis_20261102/METADATA_OUTPUT_TRUNCATION_OBSERVATION.json](feduba_semantic_transfer_diagnosis_20261102/METADATA_OUTPUT_TRUNCATION_OBSERVATION.json)
- [research/feduba_semantic_transfer_diagnosis_20261102/PUBLICATION.json](feduba_semantic_transfer_diagnosis_20261102/PUBLICATION.json)
- [research/feduba_semantic_transfer_diagnosis_20261102/RESULT.json](feduba_semantic_transfer_diagnosis_20261102/RESULT.json)
- [research/feduba_semantic_transfer_diagnosis_20261102/RUN_ONCE.json](feduba_semantic_transfer_diagnosis_20261102/RUN_ONCE.json)
- [research/feduba_semantic_transfer_diagnosis_20261102/TERMINAL_OBSERVATION.json](feduba_semantic_transfer_diagnosis_20261102/TERMINAL_OBSERVATION.json)
- [research/feduba_semantic_transfer_diagnosis_20261102/TRANSPORT_PUBLICATION.json](feduba_semantic_transfer_diagnosis_20261102/TRANSPORT_PUBLICATION.json)
- [research/feduba_semantic_transfer_diagnosis_20261102/VERIFIED.json](feduba_semantic_transfer_diagnosis_20261102/VERIFIED.json)
- [research/feduba_semantic_transfer_diagnosis_20261102/NEXT_STAGE_RATIONALE.txt](feduba_semantic_transfer_diagnosis_20261102/NEXT_STAGE_RATIONALE.txt)
- [research/feduba_targetclass_pair_20261102/.gitignore](feduba_targetclass_pair_20261102/.gitignore)
- [research/feduba_targetclass_pair_20261102/BINDING_FAILURE_TERMINAL.json](feduba_targetclass_pair_20261102/BINDING_FAILURE_TERMINAL.json)
- [research/feduba_targetclass_pair_20261102/CLEAN_FL_PROFILE.json](feduba_targetclass_pair_20261102/CLEAN_FL_PROFILE.json)
- [research/feduba_targetclass_pair_20261102/CLEAN_FL_READY.json](feduba_targetclass_pair_20261102/CLEAN_FL_READY.json)
- [research/feduba_targetclass_pair_20261102/CLEAN_FL_RESULT.json](feduba_targetclass_pair_20261102/CLEAN_FL_RESULT.json)
- [research/feduba_targetclass_pair_20261102/CLEAN_FL_VERIFIED.json](feduba_targetclass_pair_20261102/CLEAN_FL_VERIFIED.json)
- [research/feduba_targetclass_pair_20261102/controller.py](feduba_targetclass_pair_20261102/controller.py)
- [research/feduba_targetclass_pair_20261102/CONTROLLER_FAILURE.json](feduba_targetclass_pair_20261102/CONTROLLER_FAILURE.json)
- [research/feduba_targetclass_pair_20261102/CONTROLLER_ONCE.json](feduba_targetclass_pair_20261102/CONTROLLER_ONCE.json)
- [research/feduba_targetclass_pair_20261102/core.py](feduba_targetclass_pair_20261102/core.py)
- [research/feduba_targetclass_pair_20261102/evaluate_pair.py](feduba_targetclass_pair_20261102/evaluate_pair.py)
- [research/feduba_targetclass_pair_20261102/export_checkpoint_review.py](feduba_targetclass_pair_20261102/export_checkpoint_review.py)
- [research/feduba_targetclass_pair_20261102/FOUNDATION_STATE.json](feduba_targetclass_pair_20261102/FOUNDATION_STATE.json)
- [research/feduba_targetclass_pair_20261102/FU_benign_FAILURE.json](feduba_targetclass_pair_20261102/FU_benign_FAILURE.json)
- [research/feduba_targetclass_pair_20261102/FU_benign_ONCE.json](feduba_targetclass_pair_20261102/FU_benign_ONCE.json)
- [research/feduba_targetclass_pair_20261102/fu_core.py](feduba_targetclass_pair_20261102/fu_core.py)
- [research/feduba_targetclass_pair_20261102/FU_ENGINE_CPU_RESULT.json](feduba_targetclass_pair_20261102/FU_ENGINE_CPU_RESULT.json)
- [research/feduba_targetclass_pair_20261102/FU_LAUNCH_PROFILE.json](feduba_targetclass_pair_20261102/FU_LAUNCH_PROFILE.json)
- [research/feduba_targetclass_pair_20261102/FU_POLICY_CPU_RESULT.json](feduba_targetclass_pair_20261102/FU_POLICY_CPU_RESULT.json)
- [research/feduba_targetclass_pair_20261102/FU_PROFILE.json](feduba_targetclass_pair_20261102/FU_PROFILE.json)
- [research/feduba_targetclass_pair_20261102/fu_runner.py](feduba_targetclass_pair_20261102/fu_runner.py)
- [research/feduba_targetclass_pair_20261102/FU_RUN_FREEZE.json](feduba_targetclass_pair_20261102/FU_RUN_FREEZE.json)
- [research/feduba_targetclass_pair_20261102/fu_training.py](feduba_targetclass_pair_20261102/fu_training.py)
- [research/feduba_targetclass_pair_20261102/GPU_PREFLIGHT_RESULT.json](feduba_targetclass_pair_20261102/GPU_PREFLIGHT_RESULT.json)
- [research/feduba_targetclass_pair_20261102/launch_once.ps1](feduba_targetclass_pair_20261102/launch_once.ps1)
- [research/feduba_targetclass_pair_20261102/LAUNCH_PROFILE.json](feduba_targetclass_pair_20261102/LAUNCH_PROFILE.json)
- [research/feduba_targetclass_pair_20261102/model_reference.py](feduba_targetclass_pair_20261102/model_reference.py)
- [research/feduba_targetclass_pair_20261102/native_memory.py](feduba_targetclass_pair_20261102/native_memory.py)
- [research/feduba_targetclass_pair_20261102/native_processes.py](feduba_targetclass_pair_20261102/native_processes.py)
- [research/feduba_targetclass_pair_20261102/NORMAL_CASE_SELECTION.json](feduba_targetclass_pair_20261102/NORMAL_CASE_SELECTION.json)
- [research/feduba_targetclass_pair_20261102/observe_status.py](feduba_targetclass_pair_20261102/observe_status.py)
- [research/feduba_targetclass_pair_20261102/pair_binding.py](feduba_targetclass_pair_20261102/pair_binding.py)
- [research/feduba_targetclass_pair_20261102/pair_eval_core.py](feduba_targetclass_pair_20261102/pair_eval_core.py)
- [research/feduba_targetclass_pair_20261102/PAIR_EVAL_CPU_RESULT.json](feduba_targetclass_pair_20261102/PAIR_EVAL_CPU_RESULT.json)
- [research/feduba_targetclass_pair_20261102/PAIR_EVAL_LAUNCH_PROFILE.json](feduba_targetclass_pair_20261102/PAIR_EVAL_LAUNCH_PROFILE.json)
- [research/feduba_targetclass_pair_20261102/PAIR_EVAL_PROFILE.json](feduba_targetclass_pair_20261102/PAIR_EVAL_PROFILE.json)
- [research/feduba_targetclass_pair_20261102/PAIR_EVAL_RUN_FREEZE.json](feduba_targetclass_pair_20261102/PAIR_EVAL_RUN_FREEZE.json)
- [research/feduba_targetclass_pair_20261102/PREPARATION_RESULT.json](feduba_targetclass_pair_20261102/PREPARATION_RESULT.json)
- [research/feduba_targetclass_pair_20261102/PREPARE_ONCE.json](feduba_targetclass_pair_20261102/PREPARE_ONCE.json)
- [research/feduba_targetclass_pair_20261102/prepare_target_selection.py](feduba_targetclass_pair_20261102/prepare_target_selection.py)
- [research/feduba_targetclass_pair_20261102/PROTOCOL.txt](feduba_targetclass_pair_20261102/PROTOCOL.txt)
- [research/feduba_targetclass_pair_20261102/runtime_common.py](feduba_targetclass_pair_20261102/runtime_common.py)
- [research/feduba_targetclass_pair_20261102/RUN_FREEZE.json](feduba_targetclass_pair_20261102/RUN_FREEZE.json)
- [research/feduba_targetclass_pair_20261102/RUN_PUBLICATION.json](feduba_targetclass_pair_20261102/RUN_PUBLICATION.json)
- [research/feduba_targetclass_pair_20261102/source_checks.py](feduba_targetclass_pair_20261102/source_checks.py)
- [research/feduba_targetclass_pair_20261102/SOURCE_CHECK_RESULT.json](feduba_targetclass_pair_20261102/SOURCE_CHECK_RESULT.json)
- [research/feduba_targetclass_pair_20261102/SOURCE_FREEZE.json](feduba_targetclass_pair_20261102/SOURCE_FREEZE.json)
- [research/feduba_targetclass_pair_20261102/SOURCE_PROFILE.json](feduba_targetclass_pair_20261102/SOURCE_PROFILE.json)
- [research/feduba_targetclass_pair_20261102/SOURCE_PUBLICATION.json](feduba_targetclass_pair_20261102/SOURCE_PUBLICATION.json)
- [research/feduba_targetclass_pair_20261102/TASK_ONCE.json](feduba_targetclass_pair_20261102/TASK_ONCE.json)
- [research/feduba_targetclass_pair_20261102/trigger_binding.py](feduba_targetclass_pair_20261102/trigger_binding.py)
- [research/feduba_targetclass_pair_20261102/TRIGGER_SOURCE_BINDING.json](feduba_targetclass_pair_20261102/TRIGGER_SOURCE_BINDING.json)
- [research/feduba_targetclass_pair_20261102/verify_fu.py](feduba_targetclass_pair_20261102/verify_fu.py)
- [research/feduba_targetclass_pair_20261102/verify_pair_evaluation.py](feduba_targetclass_pair_20261102/verify_pair_evaluation.py)
- [research/feduba_targetclass_launch_recovery_20261102/INVOCATION_FAILURE.json](feduba_targetclass_launch_recovery_20261102/INVOCATION_FAILURE.json)
- [research/feduba_targetclass_launch_recovery_20261102/INVOCATION_ONCE.json](feduba_targetclass_launch_recovery_20261102/INVOCATION_ONCE.json)
- [research/feduba_targetclass_launch_recovery_20261102/invoke_registered_launch_once.py](feduba_targetclass_launch_recovery_20261102/invoke_registered_launch_once.py)
- [research/feduba_targetclass_launch_recovery_20261102/PREBODY_FAILURE_OBSERVATION.json](feduba_targetclass_launch_recovery_20261102/PREBODY_FAILURE_OBSERVATION.json)
- [research/feduba_targetclass_launch_recovery_20261102/PROFILE.json](feduba_targetclass_launch_recovery_20261102/PROFILE.json)
- [research/feduba_targetclass_launch_recovery_20261102/PROTOCOL.txt](feduba_targetclass_launch_recovery_20261102/PROTOCOL.txt)
- [research/feduba_targetclass_launch_recovery_20261102/PUBLICATION.json](feduba_targetclass_launch_recovery_20261102/PUBLICATION.json)
- [research/feduba_targetclass_launch_recovery_20261102/SOURCE_FREEZE.json](feduba_targetclass_launch_recovery_20261102/SOURCE_FREEZE.json)
- [research/feduba_targetclass_launch_recovery_v2_20261102/INVOCATION_FAILURE.json](feduba_targetclass_launch_recovery_v2_20261102/INVOCATION_FAILURE.json)
- [research/feduba_targetclass_launch_recovery_v2_20261102/INVOCATION_ONCE.json](feduba_targetclass_launch_recovery_v2_20261102/INVOCATION_ONCE.json)
- [research/feduba_targetclass_launch_recovery_v2_20261102/invoke_registered_launch_once.py](feduba_targetclass_launch_recovery_v2_20261102/invoke_registered_launch_once.py)
- [research/feduba_targetclass_launch_recovery_v2_20261102/PRIOR_INVOCATION_FAILURE.json](feduba_targetclass_launch_recovery_v2_20261102/PRIOR_INVOCATION_FAILURE.json)
- [research/feduba_targetclass_launch_recovery_v2_20261102/PROFILE.json](feduba_targetclass_launch_recovery_v2_20261102/PROFILE.json)
- [research/feduba_targetclass_launch_recovery_v2_20261102/PROTOCOL.txt](feduba_targetclass_launch_recovery_v2_20261102/PROTOCOL.txt)
- [research/feduba_targetclass_launch_recovery_v2_20261102/PUBLICATION.json](feduba_targetclass_launch_recovery_v2_20261102/PUBLICATION.json)
- [research/feduba_targetclass_launch_recovery_v2_20261102/SOURCE_FREEZE.json](feduba_targetclass_launch_recovery_v2_20261102/SOURCE_FREEZE.json)
- [research/feduba_targetclass_launch_recovery_v3_20261102/INVOCATION_ONCE.json](feduba_targetclass_launch_recovery_v3_20261102/INVOCATION_ONCE.json)
- [research/feduba_targetclass_launch_recovery_v3_20261102/INVOCATION_RESULT.json](feduba_targetclass_launch_recovery_v3_20261102/INVOCATION_RESULT.json)
- [research/feduba_targetclass_launch_recovery_v3_20261102/invoke_registered_launch_once.py](feduba_targetclass_launch_recovery_v3_20261102/invoke_registered_launch_once.py)
- [research/feduba_targetclass_launch_recovery_v3_20261102/PRIOR_INVOCATION_FAILURE.json](feduba_targetclass_launch_recovery_v3_20261102/PRIOR_INVOCATION_FAILURE.json)
- [research/feduba_targetclass_launch_recovery_v3_20261102/PROFILE.json](feduba_targetclass_launch_recovery_v3_20261102/PROFILE.json)
- [research/feduba_targetclass_launch_recovery_v3_20261102/PROTOCOL.txt](feduba_targetclass_launch_recovery_v3_20261102/PROTOCOL.txt)
- [research/feduba_targetclass_launch_recovery_v3_20261102/PUBLICATION.json](feduba_targetclass_launch_recovery_v3_20261102/PUBLICATION.json)
- [research/feduba_targetclass_launch_recovery_v3_20261102/SOURCE_FREEZE.json](feduba_targetclass_launch_recovery_v3_20261102/SOURCE_FREEZE.json)
- [research/feduba_targetclass_pair_recovery_20261102/.gitignore](feduba_targetclass_pair_recovery_20261102/.gitignore)
- [research/feduba_targetclass_pair_recovery_20261102/CLEAN_FL_PROFILE.json](feduba_targetclass_pair_recovery_20261102/CLEAN_FL_PROFILE.json)
- [research/feduba_targetclass_pair_recovery_20261102/CLEAN_FL_READY.json](feduba_targetclass_pair_recovery_20261102/CLEAN_FL_READY.json)
- [research/feduba_targetclass_pair_recovery_20261102/CLEAN_FL_RESULT.json](feduba_targetclass_pair_recovery_20261102/CLEAN_FL_RESULT.json)
- [research/feduba_targetclass_pair_recovery_20261102/CLEAN_FL_VERIFIED.json](feduba_targetclass_pair_recovery_20261102/CLEAN_FL_VERIFIED.json)
- [research/feduba_targetclass_pair_recovery_20261102/controller.py](feduba_targetclass_pair_recovery_20261102/controller.py)
- [research/feduba_targetclass_pair_recovery_20261102/core.py](feduba_targetclass_pair_recovery_20261102/core.py)
- [research/feduba_targetclass_pair_recovery_20261102/evaluate_pair.py](feduba_targetclass_pair_recovery_20261102/evaluate_pair.py)
- [research/feduba_targetclass_pair_recovery_20261102/export_checkpoint_review.py](feduba_targetclass_pair_recovery_20261102/export_checkpoint_review.py)
- [research/feduba_targetclass_pair_recovery_20261102/FOUNDATION_STATE.json](feduba_targetclass_pair_recovery_20261102/FOUNDATION_STATE.json)
- [research/feduba_targetclass_pair_recovery_20261102/fu_core.py](feduba_targetclass_pair_recovery_20261102/fu_core.py)
- [research/feduba_targetclass_pair_recovery_20261102/FU_ENGINE_CPU_RESULT.json](feduba_targetclass_pair_recovery_20261102/FU_ENGINE_CPU_RESULT.json)
- [research/feduba_targetclass_pair_recovery_20261102/FU_LAUNCH_PROFILE.json](feduba_targetclass_pair_recovery_20261102/FU_LAUNCH_PROFILE.json)
- [research/feduba_targetclass_pair_recovery_20261102/FU_POLICY_CPU_RESULT.json](feduba_targetclass_pair_recovery_20261102/FU_POLICY_CPU_RESULT.json)
- [research/feduba_targetclass_pair_recovery_20261102/FU_PROFILE.json](feduba_targetclass_pair_recovery_20261102/FU_PROFILE.json)
- [research/feduba_targetclass_pair_recovery_20261102/fu_runner.py](feduba_targetclass_pair_recovery_20261102/fu_runner.py)
- [research/feduba_targetclass_pair_recovery_20261102/FU_RUN_FREEZE.json](feduba_targetclass_pair_recovery_20261102/FU_RUN_FREEZE.json)
- [research/feduba_targetclass_pair_recovery_20261102/fu_training.py](feduba_targetclass_pair_recovery_20261102/fu_training.py)
- [research/feduba_targetclass_pair_recovery_20261102/GPU_PREFLIGHT_RESULT.json](feduba_targetclass_pair_recovery_20261102/GPU_PREFLIGHT_RESULT.json)
- [research/feduba_targetclass_pair_recovery_20261102/launch_once.ps1](feduba_targetclass_pair_recovery_20261102/launch_once.ps1)
- [research/feduba_targetclass_pair_recovery_20261102/LAUNCH_PROFILE.json](feduba_targetclass_pair_recovery_20261102/LAUNCH_PROFILE.json)
- [research/feduba_targetclass_pair_recovery_20261102/launch_via_ssh_once.py](feduba_targetclass_pair_recovery_20261102/launch_via_ssh_once.py)
- [research/feduba_targetclass_pair_recovery_20261102/LOCAL_LAUNCH_ONCE.json](feduba_targetclass_pair_recovery_20261102/LOCAL_LAUNCH_ONCE.json)
- [research/feduba_targetclass_pair_recovery_20261102/LOCAL_LAUNCH_RESULT.json](feduba_targetclass_pair_recovery_20261102/LOCAL_LAUNCH_RESULT.json)
- [research/feduba_targetclass_pair_recovery_20261102/model_reference.py](feduba_targetclass_pair_recovery_20261102/model_reference.py)
- [research/feduba_targetclass_pair_recovery_20261102/MONITOR_FREEZE.json](feduba_targetclass_pair_recovery_20261102/MONITOR_FREEZE.json)
- [research/feduba_targetclass_pair_recovery_20261102/MONITOR_FREEZE_V2.json](feduba_targetclass_pair_recovery_20261102/MONITOR_FREEZE_V2.json)
- [research/feduba_targetclass_pair_recovery_20261102/MONITOR_PROTOCOL.txt](feduba_targetclass_pair_recovery_20261102/MONITOR_PROTOCOL.txt)
- [research/feduba_targetclass_pair_recovery_20261102/native_memory.py](feduba_targetclass_pair_recovery_20261102/native_memory.py)
- [research/feduba_targetclass_pair_recovery_20261102/native_processes.py](feduba_targetclass_pair_recovery_20261102/native_processes.py)
- [research/feduba_targetclass_pair_recovery_20261102/NORMAL_CASE_SELECTION.json](feduba_targetclass_pair_recovery_20261102/NORMAL_CASE_SELECTION.json)
- [research/feduba_targetclass_pair_recovery_20261102/observe_status.py](feduba_targetclass_pair_recovery_20261102/observe_status.py)
- [research/feduba_targetclass_pair_recovery_20261102/observe_status_v2.py](feduba_targetclass_pair_recovery_20261102/observe_status_v2.py)
- [research/feduba_targetclass_pair_recovery_20261102/pair_binding.py](feduba_targetclass_pair_recovery_20261102/pair_binding.py)
- [research/feduba_targetclass_pair_recovery_20261102/pair_eval_core.py](feduba_targetclass_pair_recovery_20261102/pair_eval_core.py)
- [research/feduba_targetclass_pair_recovery_20261102/PAIR_EVAL_CPU_RESULT.json](feduba_targetclass_pair_recovery_20261102/PAIR_EVAL_CPU_RESULT.json)
- [research/feduba_targetclass_pair_recovery_20261102/PAIR_EVAL_LAUNCH_PROFILE.json](feduba_targetclass_pair_recovery_20261102/PAIR_EVAL_LAUNCH_PROFILE.json)
- [research/feduba_targetclass_pair_recovery_20261102/PAIR_EVAL_PROFILE.json](feduba_targetclass_pair_recovery_20261102/PAIR_EVAL_PROFILE.json)
- [research/feduba_targetclass_pair_recovery_20261102/PAIR_EVAL_RUN_FREEZE.json](feduba_targetclass_pair_recovery_20261102/PAIR_EVAL_RUN_FREEZE.json)
- [research/feduba_targetclass_pair_recovery_20261102/PREPARATION_RESULT.json](feduba_targetclass_pair_recovery_20261102/PREPARATION_RESULT.json)
- [research/feduba_targetclass_pair_recovery_20261102/prepare_from_fixed_selection.py](feduba_targetclass_pair_recovery_20261102/prepare_from_fixed_selection.py)
- [research/feduba_targetclass_pair_recovery_20261102/PREPARE_ONCE.json](feduba_targetclass_pair_recovery_20261102/PREPARE_ONCE.json)
- [research/feduba_targetclass_pair_recovery_20261102/PRIOR_BINDING_FAILURE_TERMINAL.json](feduba_targetclass_pair_recovery_20261102/PRIOR_BINDING_FAILURE_TERMINAL.json)
- [research/feduba_targetclass_pair_recovery_20261102/PROTOCOL.txt](feduba_targetclass_pair_recovery_20261102/PROTOCOL.txt)
- [research/feduba_targetclass_pair_recovery_20261102/REPORT_KO.txt](feduba_targetclass_pair_recovery_20261102/REPORT_KO.txt)
- [research/feduba_targetclass_pair_recovery_20261102/RUNNING_OBSERVATION.json](feduba_targetclass_pair_recovery_20261102/RUNNING_OBSERVATION.json)
- [research/feduba_targetclass_pair_recovery_20261102/runtime_common.py](feduba_targetclass_pair_recovery_20261102/runtime_common.py)
- [research/feduba_targetclass_pair_recovery_20261102/RUN_FREEZE.json](feduba_targetclass_pair_recovery_20261102/RUN_FREEZE.json)
- [research/feduba_targetclass_pair_recovery_20261102/RUN_PUBLICATION.json](feduba_targetclass_pair_recovery_20261102/RUN_PUBLICATION.json)
- [research/feduba_targetclass_pair_recovery_20261102/source_checks.py](feduba_targetclass_pair_recovery_20261102/source_checks.py)
- [research/feduba_targetclass_pair_recovery_20261102/SOURCE_CHECK_RESULT.json](feduba_targetclass_pair_recovery_20261102/SOURCE_CHECK_RESULT.json)
- [research/feduba_targetclass_pair_recovery_20261102/SOURCE_FREEZE.json](feduba_targetclass_pair_recovery_20261102/SOURCE_FREEZE.json)
- [research/feduba_targetclass_pair_recovery_20261102/SOURCE_PROFILE.json](feduba_targetclass_pair_recovery_20261102/SOURCE_PROFILE.json)
- [research/feduba_targetclass_pair_recovery_20261102/SOURCE_PUBLICATION.json](feduba_targetclass_pair_recovery_20261102/SOURCE_PUBLICATION.json)
- [research/feduba_targetclass_pair_recovery_20261102/trigger_binding.py](feduba_targetclass_pair_recovery_20261102/trigger_binding.py)
- [research/feduba_targetclass_pair_recovery_20261102/TRIGGER_SOURCE_BINDING.json](feduba_targetclass_pair_recovery_20261102/TRIGGER_SOURCE_BINDING.json)
- [research/feduba_targetclass_pair_recovery_20261102/verify_fu.py](feduba_targetclass_pair_recovery_20261102/verify_fu.py)
- [research/feduba_targetclass_pair_recovery_20261102/verify_pair_evaluation.py](feduba_targetclass_pair_recovery_20261102/verify_pair_evaluation.py)
- [research/feduba_targetclass_pair_recovery_20261102/ROUND_PROGRESS_OBSERVATION.json](feduba_targetclass_pair_recovery_20261102/ROUND_PROGRESS_OBSERVATION.json)
- [research/feduba_targetclass_pair_recovery_20261102/FU_benign_RESULT.json](feduba_targetclass_pair_recovery_20261102/FU_benign_RESULT.json)
- [research/feduba_targetclass_pair_recovery_20261102/BENIGN_TRAINING_COMPLETION_OBSERVATION.json](feduba_targetclass_pair_recovery_20261102/BENIGN_TRAINING_COMPLETION_OBSERVATION.json)
- [research/feduba_targetclass_pair_recovery_20261102/BENIGN_TRAINING_COMPLETION_SUMMARY.json](feduba_targetclass_pair_recovery_20261102/BENIGN_TRAINING_COMPLETION_SUMMARY.json)
- [research/feduba_targetclass_pair_recovery_20261102/BENIGN_TRAINING_COMPLETION_REPORT_KO.txt](feduba_targetclass_pair_recovery_20261102/BENIGN_TRAINING_COMPLETION_REPORT_KO.txt)
- [research/feduba_targetclass_pair_recovery_20261102/FU_benign_VERIFIED.json](feduba_targetclass_pair_recovery_20261102/FU_benign_VERIFIED.json)
- [research/feduba_targetclass_pair_recovery_20261102/BENIGN_AUDIT_COMPLETION_OBSERVATION.json](feduba_targetclass_pair_recovery_20261102/BENIGN_AUDIT_COMPLETION_OBSERVATION.json)
- [research/feduba_targetclass_pair_recovery_20261102/BENIGN_AUDIT_COMPLETION_SUMMARY.json](feduba_targetclass_pair_recovery_20261102/BENIGN_AUDIT_COMPLETION_SUMMARY.json)
- [research/feduba_targetclass_pair_recovery_20261102/BENIGN_AUDIT_COMPLETION_REPORT_KO.txt](feduba_targetclass_pair_recovery_20261102/BENIGN_AUDIT_COMPLETION_REPORT_KO.txt)
- [research/feduba_targetclass_pair_recovery_20261102/FU_attack_RESULT.json](feduba_targetclass_pair_recovery_20261102/FU_attack_RESULT.json)
- [research/feduba_targetclass_pair_recovery_20261102/ATTACK_TRAINING_COMPLETION_OBSERVATION.json](feduba_targetclass_pair_recovery_20261102/ATTACK_TRAINING_COMPLETION_OBSERVATION.json)
- [research/feduba_targetclass_pair_recovery_20261102/ATTACK_TRAINING_COMPLETION_SUMMARY.json](feduba_targetclass_pair_recovery_20261102/ATTACK_TRAINING_COMPLETION_SUMMARY.json)
- [research/feduba_targetclass_pair_recovery_20261102/ATTACK_TRAINING_COMPLETION_REPORT_KO.txt](feduba_targetclass_pair_recovery_20261102/ATTACK_TRAINING_COMPLETION_REPORT_KO.txt)
- [research/feduba_targetclass_pair_recovery_20261102/FU_attack_VERIFIED.json](feduba_targetclass_pair_recovery_20261102/FU_attack_VERIFIED.json)
- [research/feduba_targetclass_pair_recovery_20261102/PAIR_EVAL_RESULT.json](feduba_targetclass_pair_recovery_20261102/PAIR_EVAL_RESULT.json)
- [research/feduba_targetclass_pair_recovery_20261102/PAIR_EVAL_VERIFIED.json](feduba_targetclass_pair_recovery_20261102/PAIR_EVAL_VERIFIED.json)
- [research/feduba_targetclass_pair_recovery_20261102/COMPLETION.json](feduba_targetclass_pair_recovery_20261102/COMPLETION.json)
- [research/feduba_targetclass_pair_recovery_20261102/REMOTE_CHECKPOINT_REVIEW.json](feduba_targetclass_pair_recovery_20261102/REMOTE_CHECKPOINT_REVIEW.json)
- [research/feduba_targetclass_pair_recovery_20261102/FINAL_TERMINAL_OBSERVATION.json](feduba_targetclass_pair_recovery_20261102/FINAL_TERMINAL_OBSERVATION.json)
- [research/feduba_targetclass_pair_recovery_20261102/FINAL_RESULT_SUMMARY.json](feduba_targetclass_pair_recovery_20261102/FINAL_RESULT_SUMMARY.json)
- [research/feduba_targetclass_pair_recovery_20261102/FINAL_REPORT_KO.txt](feduba_targetclass_pair_recovery_20261102/FINAL_REPORT_KO.txt)
- [research/feduba_targetclass_pair_recovery_20261102/PAPER_COMPARISON.txt](feduba_targetclass_pair_recovery_20261102/PAPER_COMPARISON.txt)
- [research/feduba_fixed_cohort_review_20261103/HISTORY_METADATA.json](feduba_fixed_cohort_review_20261103/HISTORY_METADATA.json)
- [research/feduba_fixed_cohort_review_20261103/REPORT_KO.txt](feduba_fixed_cohort_review_20261103/REPORT_KO.txt)
- [research/feduba_fixed_cohort_review_20261103/REVIEW_FREEZE.json](feduba_fixed_cohort_review_20261103/REVIEW_FREEZE.json)
- [research/feduba_fixed_cohort_review_20261103/REVIEW_PROFILE.json](feduba_fixed_cohort_review_20261103/REVIEW_PROFILE.json)
- [research/feduba_fixed10_foundation_20261103/.gitignore](feduba_fixed10_foundation_20261103/.gitignore)
- [research/feduba_fixed10_foundation_20261103/CLEAN_FL_FREEZE.json](feduba_fixed10_foundation_20261103/CLEAN_FL_FREEZE.json)
- [research/feduba_fixed10_foundation_20261103/CLEAN_FL_PROFILE.json](feduba_fixed10_foundation_20261103/CLEAN_FL_PROFILE.json)
- [research/feduba_fixed10_foundation_20261103/CLEAN_FL_READY.json](feduba_fixed10_foundation_20261103/CLEAN_FL_READY.json)
- [research/feduba_fixed10_foundation_20261103/clean_fl_runner.py](feduba_fixed10_foundation_20261103/clean_fl_runner.py)
- [research/feduba_fixed10_foundation_20261103/core.py](feduba_fixed10_foundation_20261103/core.py)
- [research/feduba_fixed10_foundation_20261103/foundation_binding.py](feduba_fixed10_foundation_20261103/foundation_binding.py)
- [research/feduba_fixed10_foundation_20261103/foundation_controller.py](feduba_fixed10_foundation_20261103/foundation_controller.py)
- [research/feduba_fixed10_foundation_20261103/GPU_PREFLIGHT_RESULT.json](feduba_fixed10_foundation_20261103/GPU_PREFLIGHT_RESULT.json)
- [research/feduba_fixed10_foundation_20261103/launch_once.ps1](feduba_fixed10_foundation_20261103/launch_once.ps1)
- [research/feduba_fixed10_foundation_20261103/LAUNCH_PROFILE.json](feduba_fixed10_foundation_20261103/LAUNCH_PROFILE.json)
- [research/feduba_fixed10_foundation_20261103/launch_via_ssh_once.py](feduba_fixed10_foundation_20261103/launch_via_ssh_once.py)
- [research/feduba_fixed10_foundation_20261103/LOCAL_LAUNCH_ONCE.json](feduba_fixed10_foundation_20261103/LOCAL_LAUNCH_ONCE.json)
- [research/feduba_fixed10_foundation_20261103/LOCAL_LAUNCH_RESULT.json](feduba_fixed10_foundation_20261103/LOCAL_LAUNCH_RESULT.json)
- [research/feduba_fixed10_foundation_20261103/model_reference.py](feduba_fixed10_foundation_20261103/model_reference.py)
- [research/feduba_fixed10_foundation_20261103/MONITOR_FREEZE.json](feduba_fixed10_foundation_20261103/MONITOR_FREEZE.json)
- [research/feduba_fixed10_foundation_20261103/MONITOR_PROTOCOL.txt](feduba_fixed10_foundation_20261103/MONITOR_PROTOCOL.txt)
- [research/feduba_fixed10_foundation_20261103/native_memory.py](feduba_fixed10_foundation_20261103/native_memory.py)
- [research/feduba_fixed10_foundation_20261103/native_processes.py](feduba_fixed10_foundation_20261103/native_processes.py)
- [research/feduba_fixed10_foundation_20261103/observe_status.py](feduba_fixed10_foundation_20261103/observe_status.py)
- [research/feduba_fixed10_foundation_20261103/PREPARATION_RESULT.json](feduba_fixed10_foundation_20261103/PREPARATION_RESULT.json)
- [research/feduba_fixed10_foundation_20261103/prepare_foundation.py](feduba_fixed10_foundation_20261103/prepare_foundation.py)
- [research/feduba_fixed10_foundation_20261103/PREPARE_ONCE.json](feduba_fixed10_foundation_20261103/PREPARE_ONCE.json)
- [research/feduba_fixed10_foundation_20261103/PROTOCOL.txt](feduba_fixed10_foundation_20261103/PROTOCOL.txt)
- [research/feduba_fixed10_foundation_20261103/PUBLICATION_BYTE_CHECKS.json](feduba_fixed10_foundation_20261103/PUBLICATION_BYTE_CHECKS.json)
- [research/feduba_fixed10_foundation_20261103/REPORT_KO.txt](feduba_fixed10_foundation_20261103/REPORT_KO.txt)
- [research/feduba_fixed10_foundation_20261103/RUNNING_OBSERVATION.json](feduba_fixed10_foundation_20261103/RUNNING_OBSERVATION.json)
- [research/feduba_fixed10_foundation_20261103/runtime_common.py](feduba_fixed10_foundation_20261103/runtime_common.py)
- [research/feduba_fixed10_foundation_20261103/RUN_FREEZE.json](feduba_fixed10_foundation_20261103/RUN_FREEZE.json)
- [research/feduba_fixed10_foundation_20261103/RUN_PUBLICATION.json](feduba_fixed10_foundation_20261103/RUN_PUBLICATION.json)
- [research/feduba_fixed10_foundation_20261103/source_checks.py](feduba_fixed10_foundation_20261103/source_checks.py)
- [research/feduba_fixed10_foundation_20261103/SOURCE_CHECK_RESULT.json](feduba_fixed10_foundation_20261103/SOURCE_CHECK_RESULT.json)
- [research/feduba_fixed10_foundation_20261103/SOURCE_FREEZE.json](feduba_fixed10_foundation_20261103/SOURCE_FREEZE.json)
- [research/feduba_fixed10_foundation_20261103/SOURCE_PROFILE.json](feduba_fixed10_foundation_20261103/SOURCE_PROFILE.json)
- [research/feduba_fixed10_foundation_20261103/SOURCE_PUBLICATION.json](feduba_fixed10_foundation_20261103/SOURCE_PUBLICATION.json)
- [research/feduba_fixed10_foundation_20261103/verify_clean_fl.py](feduba_fixed10_foundation_20261103/verify_clean_fl.py)
- [research/feduba_fixed10_clean_delivery_20261103/PROTOCOL.txt](feduba_fixed10_clean_delivery_20261103/PROTOCOL.txt)
- [research/feduba_fixed10_clean_delivery_20261103/REPORT_KO.txt](feduba_fixed10_clean_delivery_20261103/REPORT_KO.txt)
- [research/feduba_fixed10_clean_delivery_20261103/SOURCE_FREEZE.json](feduba_fixed10_clean_delivery_20261103/SOURCE_FREEZE.json)
- [research/feduba_fixed10_clean_delivery_20261103/SOURCE_PROFILE.json](feduba_fixed10_clean_delivery_20261103/SOURCE_PROFILE.json)
- [research/feduba_fixed10_clean_delivery_20261103/SOURCE_PUBLICATION.json](feduba_fixed10_clean_delivery_20261103/SOURCE_PUBLICATION.json)
- [research/feduba_fixed10_clean_delivery_20261103/SOURCE_REVIEW_RESULT.json](feduba_fixed10_clean_delivery_20261103/SOURCE_REVIEW_RESULT.json)
- [research/feduba_fixed10_clean_delivery_20261103/clean_delivery_binding.py](feduba_fixed10_clean_delivery_20261103/clean_delivery_binding.py)
- [research/feduba_fixed10_clean_delivery_20261103/export_clean_review.py](feduba_fixed10_clean_delivery_20261103/export_clean_review.py)
- [research/feduba_fixed10_clean_delivery_20261103/launch_once.ps1](feduba_fixed10_clean_delivery_20261103/launch_once.ps1)
- [research/feduba_fixed10_clean_delivery_20261103/launch_via_ssh_once.py](feduba_fixed10_clean_delivery_20261103/launch_via_ssh_once.py)
- [research/feduba_fixed10_clean_delivery_20261103/model_reference.py](feduba_fixed10_clean_delivery_20261103/model_reference.py)
- [research/feduba_fixed10_clean_delivery_20261103/native_memory.py](feduba_fixed10_clean_delivery_20261103/native_memory.py)
- [research/feduba_fixed10_clean_delivery_20261103/native_processes.py](feduba_fixed10_clean_delivery_20261103/native_processes.py)
- [research/feduba_fixed10_clean_delivery_20261103/prepare_actual.py](feduba_fixed10_clean_delivery_20261103/prepare_actual.py)
- [research/feduba_fixed10_clean_delivery_20261103/prepare_via_ssh_once.py](feduba_fixed10_clean_delivery_20261103/prepare_via_ssh_once.py)
- [research/feduba_fixed10_clean_delivery_20261103/register_clean_case.py](feduba_fixed10_clean_delivery_20261103/register_clean_case.py)
- [research/feduba_fixed10_clean_delivery_20261103/review_loader.py](feduba_fixed10_clean_delivery_20261103/review_loader.py)
- [research/feduba_fixed10_clean_delivery_20261103/runtime_common.py](feduba_fixed10_clean_delivery_20261103/runtime_common.py)
- [research/feduba_fixed10_clean_delivery_20261103/source_review.py](feduba_fixed10_clean_delivery_20261103/source_review.py)
- [research/feduba_fixed10_sss_20261103/COPY_PROVENANCE.json](feduba_fixed10_sss_20261103/COPY_PROVENANCE.json)
- [research/feduba_fixed10_sss_20261103/MONITOR_PROTOCOL.txt](feduba_fixed10_sss_20261103/MONITOR_PROTOCOL.txt)
- [research/feduba_fixed10_sss_20261103/PROTOCOL.txt](feduba_fixed10_sss_20261103/PROTOCOL.txt)
- [research/feduba_fixed10_sss_20261103/REPORT_KO.txt](feduba_fixed10_sss_20261103/REPORT_KO.txt)
- [research/feduba_fixed10_sss_20261103/SOURCE_FREEZE.json](feduba_fixed10_sss_20261103/SOURCE_FREEZE.json)
- [research/feduba_fixed10_sss_20261103/SOURCE_PROFILE.json](feduba_fixed10_sss_20261103/SOURCE_PROFILE.json)
- [research/feduba_fixed10_sss_20261103/SOURCE_PUBLICATION.json](feduba_fixed10_sss_20261103/SOURCE_PUBLICATION.json)
- [research/feduba_fixed10_sss_20261103/SOURCE_REVIEW_REPORT_KO.txt](feduba_fixed10_sss_20261103/SOURCE_REVIEW_REPORT_KO.txt)
- [research/feduba_fixed10_sss_20261103/SOURCE_REVIEW_RESULT.json](feduba_fixed10_sss_20261103/SOURCE_REVIEW_RESULT.json)
- [research/feduba_fixed10_sss_20261103/SSS_LOGGER_CPU2_RESULT.json](feduba_fixed10_sss_20261103/SSS_LOGGER_CPU2_RESULT.json)
- [research/feduba_fixed10_sss_20261103/SSS_NUMERIC_POLICY.json](feduba_fixed10_sss_20261103/SSS_NUMERIC_POLICY.json)
- [research/feduba_fixed10_sss_20261103/SSS_PROFILE.json](feduba_fixed10_sss_20261103/SSS_PROFILE.json)
- [research/feduba_fixed10_sss_20261103/TRIGGER_SOURCE_BINDING.json](feduba_fixed10_sss_20261103/TRIGGER_SOURCE_BINDING.json)
- [research/feduba_fixed10_sss_20261103/core.py](feduba_fixed10_sss_20261103/core.py)
- [research/feduba_fixed10_sss_20261103/launch_once.ps1](feduba_fixed10_sss_20261103/launch_once.ps1)
- [research/feduba_fixed10_sss_20261103/launch_via_ssh_once.py](feduba_fixed10_sss_20261103/launch_via_ssh_once.py)
- [research/feduba_fixed10_sss_20261103/model_reference.py](feduba_fixed10_sss_20261103/model_reference.py)
- [research/feduba_fixed10_sss_20261103/native_memory.py](feduba_fixed10_sss_20261103/native_memory.py)
- [research/feduba_fixed10_sss_20261103/native_processes.py](feduba_fixed10_sss_20261103/native_processes.py)
- [research/feduba_fixed10_sss_20261103/observe_status.py](feduba_fixed10_sss_20261103/observe_status.py)
- [research/feduba_fixed10_sss_20261103/pair_binding.py](feduba_fixed10_sss_20261103/pair_binding.py)
- [research/feduba_fixed10_sss_20261103/prepare_sss.py](feduba_fixed10_sss_20261103/prepare_sss.py)
- [research/feduba_fixed10_sss_20261103/prepare_via_ssh_once.py](feduba_fixed10_sss_20261103/prepare_via_ssh_once.py)
- [research/feduba_fixed10_sss_20261103/runtime_common.py](feduba_fixed10_sss_20261103/runtime_common.py)
- [research/feduba_fixed10_sss_20261103/source_review.py](feduba_fixed10_sss_20261103/source_review.py)
- [research/feduba_fixed10_sss_20261103/sss_controller.py](feduba_fixed10_sss_20261103/sss_controller.py)
- [research/feduba_fixed10_sss_20261103/sss_logging.py](feduba_fixed10_sss_20261103/sss_logging.py)
- [research/feduba_fixed10_sss_20261103/sss_runner.py](feduba_fixed10_sss_20261103/sss_runner.py)
- [research/feduba_fixed10_sss_20261103/trigger_binding.py](feduba_fixed10_sss_20261103/trigger_binding.py)
- [research/feduba_fixed10_sss_20261103/verify_sss.py](feduba_fixed10_sss_20261103/verify_sss.py)
- [research/feduba_fixed10_pair_20261103/COPY_PROVENANCE.json](feduba_fixed10_pair_20261103/COPY_PROVENANCE.json)
- [research/feduba_fixed10_pair_20261103/FU_ENGINE_CPU_RESULT.json](feduba_fixed10_pair_20261103/FU_ENGINE_CPU_RESULT.json)
- [research/feduba_fixed10_pair_20261103/FU_POLICY_CPU_RESULT.json](feduba_fixed10_pair_20261103/FU_POLICY_CPU_RESULT.json)
- [research/feduba_fixed10_pair_20261103/FU_PROFILE.json](feduba_fixed10_pair_20261103/FU_PROFILE.json)
- [research/feduba_fixed10_pair_20261103/GPU_PREFLIGHT_RESULT.json](feduba_fixed10_pair_20261103/GPU_PREFLIGHT_RESULT.json)
- [research/feduba_fixed10_pair_20261103/MONITOR_PROTOCOL.txt](feduba_fixed10_pair_20261103/MONITOR_PROTOCOL.txt)
- [research/feduba_fixed10_pair_20261103/PAIR_EVAL_CPU_RESULT.json](feduba_fixed10_pair_20261103/PAIR_EVAL_CPU_RESULT.json)
- [research/feduba_fixed10_pair_20261103/PAIR_EVAL_PROFILE.json](feduba_fixed10_pair_20261103/PAIR_EVAL_PROFILE.json)
- [research/feduba_fixed10_pair_20261103/PROTOCOL.txt](feduba_fixed10_pair_20261103/PROTOCOL.txt)
- [research/feduba_fixed10_pair_20261103/REPORT_KO.txt](feduba_fixed10_pair_20261103/REPORT_KO.txt)
- [research/feduba_fixed10_pair_20261103/SOURCE_FREEZE.json](feduba_fixed10_pair_20261103/SOURCE_FREEZE.json)
- [research/feduba_fixed10_pair_20261103/SOURCE_PROFILE.json](feduba_fixed10_pair_20261103/SOURCE_PROFILE.json)
- [research/feduba_fixed10_pair_20261103/SOURCE_PUBLICATION.json](feduba_fixed10_pair_20261103/SOURCE_PUBLICATION.json)
- [research/feduba_fixed10_pair_20261103/SOURCE_REVIEW_REPORT_KO.txt](feduba_fixed10_pair_20261103/SOURCE_REVIEW_REPORT_KO.txt)
- [research/feduba_fixed10_pair_20261103/SOURCE_REVIEW_RESULT.json](feduba_fixed10_pair_20261103/SOURCE_REVIEW_RESULT.json)
- [research/feduba_fixed10_pair_20261103/TRIGGER_SOURCE_BINDING.json](feduba_fixed10_pair_20261103/TRIGGER_SOURCE_BINDING.json)
- [research/feduba_fixed10_pair_20261103/controller.py](feduba_fixed10_pair_20261103/controller.py)
- [research/feduba_fixed10_pair_20261103/core.py](feduba_fixed10_pair_20261103/core.py)
- [research/feduba_fixed10_pair_20261103/evaluate_pair.py](feduba_fixed10_pair_20261103/evaluate_pair.py)
- [research/feduba_fixed10_pair_20261103/export_checkpoint_review.py](feduba_fixed10_pair_20261103/export_checkpoint_review.py)
- [research/feduba_fixed10_pair_20261103/fu_core.py](feduba_fixed10_pair_20261103/fu_core.py)
- [research/feduba_fixed10_pair_20261103/fu_runner.py](feduba_fixed10_pair_20261103/fu_runner.py)
- [research/feduba_fixed10_pair_20261103/fu_training.py](feduba_fixed10_pair_20261103/fu_training.py)
- [research/feduba_fixed10_pair_20261103/launch_once.ps1](feduba_fixed10_pair_20261103/launch_once.ps1)
- [research/feduba_fixed10_pair_20261103/launch_via_ssh_once.py](feduba_fixed10_pair_20261103/launch_via_ssh_once.py)
- [research/feduba_fixed10_pair_20261103/model_reference.py](feduba_fixed10_pair_20261103/model_reference.py)
- [research/feduba_fixed10_pair_20261103/native_memory.py](feduba_fixed10_pair_20261103/native_memory.py)
- [research/feduba_fixed10_pair_20261103/native_processes.py](feduba_fixed10_pair_20261103/native_processes.py)
- [research/feduba_fixed10_pair_20261103/observe_status.py](feduba_fixed10_pair_20261103/observe_status.py)
- [research/feduba_fixed10_pair_20261103/pair_binding.py](feduba_fixed10_pair_20261103/pair_binding.py)
- [research/feduba_fixed10_pair_20261103/pair_eval_core.py](feduba_fixed10_pair_20261103/pair_eval_core.py)
- [research/feduba_fixed10_pair_20261103/prepare_pair.py](feduba_fixed10_pair_20261103/prepare_pair.py)
- [research/feduba_fixed10_pair_20261103/prepare_via_ssh_once.py](feduba_fixed10_pair_20261103/prepare_via_ssh_once.py)
- [research/feduba_fixed10_pair_20261103/runtime_common.py](feduba_fixed10_pair_20261103/runtime_common.py)
- [research/feduba_fixed10_pair_20261103/source_review.py](feduba_fixed10_pair_20261103/source_review.py)
- [research/feduba_fixed10_pair_20261103/trigger_binding.py](feduba_fixed10_pair_20261103/trigger_binding.py)
- [research/feduba_fixed10_pair_20261103/verify_fu.py](feduba_fixed10_pair_20261103/verify_fu.py)
- [research/feduba_fixed10_pair_20261103/verify_pair_evaluation.py](feduba_fixed10_pair_20261103/verify_pair_evaluation.py)
- [research/feduba_fixed10_foundation_20261103/CLEAN_FL_RESULT.json](feduba_fixed10_foundation_20261103/CLEAN_FL_RESULT.json)
- [research/feduba_fixed10_foundation_20261103/CLEAN_FL_STATE.json](feduba_fixed10_foundation_20261103/CLEAN_FL_STATE.json)
- [research/feduba_fixed10_foundation_20261103/CLEAN_FL_VERIFIED.json](feduba_fixed10_foundation_20261103/CLEAN_FL_VERIFIED.json)
- [research/feduba_fixed10_foundation_20261103/COMPLETION.json](feduba_fixed10_foundation_20261103/COMPLETION.json)
- [research/feduba_fixed10_foundation_20261103/FOUNDATION_CONTROLLER_STATE.json](feduba_fixed10_foundation_20261103/FOUNDATION_CONTROLLER_STATE.json)
- [research/feduba_fixed10_foundation_20261103/TRAINING_COMPLETION_OBSERVATION.json](feduba_fixed10_foundation_20261103/TRAINING_COMPLETION_OBSERVATION.json)
- [research/feduba_fixed10_foundation_20261103/TRAINING_COMPLETION_SUMMARY.json](feduba_fixed10_foundation_20261103/TRAINING_COMPLETION_SUMMARY.json)
- [research/feduba_fixed10_foundation_20261103/FINAL_FOUNDATION_OBSERVATION.json](feduba_fixed10_foundation_20261103/FINAL_FOUNDATION_OBSERVATION.json)
- [research/feduba_fixed10_foundation_20261103/FINAL_FOUNDATION_SUMMARY.json](feduba_fixed10_foundation_20261103/FINAL_FOUNDATION_SUMMARY.json)
- [research/feduba_fixed10_foundation_20261103/FINAL_FOUNDATION_REPORT_KO.txt](feduba_fixed10_foundation_20261103/FINAL_FOUNDATION_REPORT_KO.txt)
- [research/feduba_fixed10_clean_delivery_20261103/LOCAL_PREPARE_ONCE.json](feduba_fixed10_clean_delivery_20261103/LOCAL_PREPARE_ONCE.json)
- [research/feduba_fixed10_clean_delivery_20261103/FOUNDATION_TERMINAL_CHECK.json](feduba_fixed10_clean_delivery_20261103/FOUNDATION_TERMINAL_CHECK.json)
- [research/feduba_fixed10_clean_delivery_20261103/PREPARE_ONCE.json](feduba_fixed10_clean_delivery_20261103/PREPARE_ONCE.json)
- [research/feduba_fixed10_clean_delivery_20261103/FOUNDATION_INPUT_BINDING.json](feduba_fixed10_clean_delivery_20261103/FOUNDATION_INPUT_BINDING.json)
- [research/feduba_fixed10_clean_delivery_20261103/LAUNCH_PROFILE.json](feduba_fixed10_clean_delivery_20261103/LAUNCH_PROFILE.json)
- [research/feduba_fixed10_clean_delivery_20261103/RUN_FREEZE.json](feduba_fixed10_clean_delivery_20261103/RUN_FREEZE.json)
- [research/feduba_fixed10_clean_delivery_20261103/CLEAN_EXPORT_FREEZE.json](feduba_fixed10_clean_delivery_20261103/CLEAN_EXPORT_FREEZE.json)
- [research/feduba_fixed10_clean_delivery_20261103/CLEAN_REGISTRATION_FREEZE.json](feduba_fixed10_clean_delivery_20261103/CLEAN_REGISTRATION_FREEZE.json)
- [research/feduba_fixed10_clean_delivery_20261103/observe_status.py](feduba_fixed10_clean_delivery_20261103/observe_status.py)
- [research/feduba_fixed10_clean_delivery_20261103/MONITOR_PROTOCOL.txt](feduba_fixed10_clean_delivery_20261103/MONITOR_PROTOCOL.txt)
- [research/feduba_fixed10_clean_delivery_20261103/MONITOR_FREEZE.json](feduba_fixed10_clean_delivery_20261103/MONITOR_FREEZE.json)
- [research/feduba_fixed10_sss_20261103/LOCAL_PREPARE_ONCE.json](feduba_fixed10_sss_20261103/LOCAL_PREPARE_ONCE.json)
- [research/feduba_fixed10_sss_20261103/FOUNDATION_TERMINAL_CHECK.json](feduba_fixed10_sss_20261103/FOUNDATION_TERMINAL_CHECK.json)
- [research/feduba_fixed10_sss_20261103/PREPARE_ONCE.json](feduba_fixed10_sss_20261103/PREPARE_ONCE.json)
- [research/feduba_fixed10_sss_20261103/FOUNDATION_INPUT_BINDING.json](feduba_fixed10_sss_20261103/FOUNDATION_INPUT_BINDING.json)
- [research/feduba_fixed10_sss_20261103/SSS_LAUNCH_PROFILE.json](feduba_fixed10_sss_20261103/SSS_LAUNCH_PROFILE.json)
- [research/feduba_fixed10_sss_20261103/LAUNCH_PROFILE.json](feduba_fixed10_sss_20261103/LAUNCH_PROFILE.json)
- [research/feduba_fixed10_sss_20261103/RUN_FREEZE.json](feduba_fixed10_sss_20261103/RUN_FREEZE.json)
- [research/feduba_fixed10_sss_20261103/SSS_FREEZE.json](feduba_fixed10_sss_20261103/SSS_FREEZE.json)
- [research/feduba_fixed10_sss_20261103/CLEAN_FL_RESULT.json](feduba_fixed10_sss_20261103/CLEAN_FL_RESULT.json)
- [research/feduba_fixed10_sss_20261103/CLEAN_FL_VERIFIED.json](feduba_fixed10_sss_20261103/CLEAN_FL_VERIFIED.json)
- [research/feduba_fixed10_sss_20261103/CLEAN_FL_READY.json](feduba_fixed10_sss_20261103/CLEAN_FL_READY.json)
- [research/feduba_fixed10_sss_20261103/CLEAN_FL_PROFILE.json](feduba_fixed10_sss_20261103/CLEAN_FL_PROFILE.json)
- [research/feduba_fixed10_sss_20261103/GPU_PREFLIGHT_RESULT.json](feduba_fixed10_sss_20261103/GPU_PREFLIGHT_RESULT.json)
- [research/feduba_fixed10_clean_delivery_20261103/RUN_PUBLICATION.json](feduba_fixed10_clean_delivery_20261103/RUN_PUBLICATION.json)
- [research/feduba_fixed10_clean_delivery_20261103/LOCAL_LAUNCH_ONCE.json](feduba_fixed10_clean_delivery_20261103/LOCAL_LAUNCH_ONCE.json)
- [research/feduba_fixed10_clean_delivery_20261103/LOCAL_LAUNCH_RESULT.json](feduba_fixed10_clean_delivery_20261103/LOCAL_LAUNCH_RESULT.json)
- [research/feduba_fixed10_clean_delivery_20261103/TASK_ONCE.json](feduba_fixed10_clean_delivery_20261103/TASK_ONCE.json)
- [research/feduba_fixed10_clean_delivery_20261103/CLEAN_EXPORT_ONCE.json](feduba_fixed10_clean_delivery_20261103/CLEAN_EXPORT_ONCE.json)
- [research/feduba_fixed10_clean_delivery_20261103/CLEAN_REVIEW_DELIVERY_REMOTE.json](feduba_fixed10_clean_delivery_20261103/CLEAN_REVIEW_DELIVERY_REMOTE.json)
- [research/feduba_fixed10_clean_delivery_20261103/DISLAB_REGISTRATION_CALL_ONCE.json](feduba_fixed10_clean_delivery_20261103/DISLAB_REGISTRATION_CALL_ONCE.json)
- [research/feduba_fixed10_clean_delivery_20261103/READBACK_RECOVERY_PROTOCOL.txt](feduba_fixed10_clean_delivery_20261103/READBACK_RECOVERY_PROTOCOL.txt)
- [research/feduba_fixed10_clean_delivery_20261103/LOCAL_READBACK_FAILURE_OBSERVATION.json](feduba_fixed10_clean_delivery_20261103/LOCAL_READBACK_FAILURE_OBSERVATION.json)
- [research/feduba_fixed10_clean_delivery_20261103/READBACK_RECOVERY_RESULT.json](feduba_fixed10_clean_delivery_20261103/READBACK_RECOVERY_RESULT.json)
- [research/feduba_fixed10_clean_delivery_20261103/EXPORT_COMPLETION_OBSERVATION.json](feduba_fixed10_clean_delivery_20261103/EXPORT_COMPLETION_OBSERVATION.json)
- [research/feduba_fixed10_clean_delivery_20261103/REMOTE_NORMAL_COMPLETION_SUMMARY.json](feduba_fixed10_clean_delivery_20261103/REMOTE_NORMAL_COMPLETION_SUMMARY.json)
- [research/feduba_fixed10_clean_delivery_20261103/REMOTE_NORMAL_COMPLETION_REPORT_KO.txt](feduba_fixed10_clean_delivery_20261103/REMOTE_NORMAL_COMPLETION_REPORT_KO.txt)
- [research/feduba_fixed10_sss_20261103/RUN_PUBLICATION.json](feduba_fixed10_sss_20261103/RUN_PUBLICATION.json)
- [research/feduba_fixed10_sss_20261103/LOCAL_LAUNCH_ONCE.json](feduba_fixed10_sss_20261103/LOCAL_LAUNCH_ONCE.json)
- [research/feduba_fixed10_sss_20261103/LOCAL_LAUNCH_RESULT.json](feduba_fixed10_sss_20261103/LOCAL_LAUNCH_RESULT.json)
- [research/feduba_fixed10_sss_20261103/TASK_ONCE.json](feduba_fixed10_sss_20261103/TASK_ONCE.json)
- [research/feduba_fixed10_sss_20261103/SSS_ONCE.json](feduba_fixed10_sss_20261103/SSS_ONCE.json)
- [research/feduba_fixed10_sss_20261103/SSS_AUDIT_ONCE.json](feduba_fixed10_sss_20261103/SSS_AUDIT_ONCE.json)
- [research/feduba_fixed10_sss_20261103/SSS_STATE.json](feduba_fixed10_sss_20261103/SSS_STATE.json)
- [research/feduba_fixed10_sss_20261103/SSS_CONTROLLER_STATE.json](feduba_fixed10_sss_20261103/SSS_CONTROLLER_STATE.json)
- [research/feduba_fixed10_sss_20261103/COMPLETION.json](feduba_fixed10_sss_20261103/COMPLETION.json)
- [research/feduba_fixed10_sss_20261103/SSS_COMPLETION_OBSERVATION.json](feduba_fixed10_sss_20261103/SSS_COMPLETION_OBSERVATION.json)
- [research/feduba_fixed10_sss_20261103/SSS_COMPLETION_SUMMARY.json](feduba_fixed10_sss_20261103/SSS_COMPLETION_SUMMARY.json)
- [research/feduba_fixed10_sss_20261103/SSS_COMPLETION_REPORT_KO.txt](feduba_fixed10_sss_20261103/SSS_COMPLETION_REPORT_KO.txt)
- [research/feduba_fixed10_sss_20261103/CPU_REPLAY_COUNT_DISCREPANCY.json](feduba_fixed10_sss_20261103/CPU_REPLAY_COUNT_DISCREPANCY.json)
- [research/feduba_fixed10_sss_20261103/CPU_REPLAY_COUNT_AMENDMENT_PROTOCOL.txt](feduba_fixed10_sss_20261103/CPU_REPLAY_COUNT_AMENDMENT_PROTOCOL.txt)
- [research/feduba_fixed10_sss_20261103/CPU_REPLAY_COUNT_RECONCILIATION.json](feduba_fixed10_sss_20261103/CPU_REPLAY_COUNT_RECONCILIATION.json)
- [research/feduba_fixed10_pair_20261103/LOCAL_PREPARE_ONCE.json](feduba_fixed10_pair_20261103/LOCAL_PREPARE_ONCE.json)
- [research/feduba_fixed10_pair_20261103/UPSTREAM_TERMINAL_CHECK.json](feduba_fixed10_pair_20261103/UPSTREAM_TERMINAL_CHECK.json)
- [research/feduba_fixed10_pair_20261103/PREPARE_ONCE.json](feduba_fixed10_pair_20261103/PREPARE_ONCE.json)
- [research/feduba_fixed10_pair_20261103/FOUNDATION_INPUT_BINDING.json](feduba_fixed10_pair_20261103/FOUNDATION_INPUT_BINDING.json)
- [research/feduba_fixed10_pair_20261103/FU_LAUNCH_PROFILE.json](feduba_fixed10_pair_20261103/FU_LAUNCH_PROFILE.json)
- [research/feduba_fixed10_pair_20261103/PAIR_EVAL_LAUNCH_PROFILE.json](feduba_fixed10_pair_20261103/PAIR_EVAL_LAUNCH_PROFILE.json)
- [research/feduba_fixed10_pair_20261103/LAUNCH_PROFILE.json](feduba_fixed10_pair_20261103/LAUNCH_PROFILE.json)
- [research/feduba_fixed10_pair_20261103/PREPARATION_RESULT.json](feduba_fixed10_pair_20261103/PREPARATION_RESULT.json)
- [research/feduba_fixed10_pair_20261103/RUN_FREEZE.json](feduba_fixed10_pair_20261103/RUN_FREEZE.json)
- [research/feduba_fixed10_pair_20261103/FU_RUN_FREEZE.json](feduba_fixed10_pair_20261103/FU_RUN_FREEZE.json)
- [research/feduba_fixed10_pair_20261103/PAIR_EVAL_RUN_FREEZE.json](feduba_fixed10_pair_20261103/PAIR_EVAL_RUN_FREEZE.json)
- [research/feduba_fixed10_pair_20261103/CLEAN_FL_RESULT.json](feduba_fixed10_pair_20261103/CLEAN_FL_RESULT.json)
- [research/feduba_fixed10_pair_20261103/CLEAN_FL_VERIFIED.json](feduba_fixed10_pair_20261103/CLEAN_FL_VERIFIED.json)
- [research/feduba_fixed10_pair_20261103/CLEAN_FL_READY.json](feduba_fixed10_pair_20261103/CLEAN_FL_READY.json)
- [research/feduba_fixed10_pair_20261103/CLEAN_FL_PROFILE.json](feduba_fixed10_pair_20261103/CLEAN_FL_PROFILE.json)
- [research/feduba_fixed10_pair_20261103/SSS_REPLAY_COUNT_BINDING.json](feduba_fixed10_pair_20261103/SSS_REPLAY_COUNT_BINDING.json)
- [research/feduba_fixed10_pair_20261103/ACTUAL_RUN_REPORT_KO.txt](feduba_fixed10_pair_20261103/ACTUAL_RUN_REPORT_KO.txt)
- [research/feduba_fixed10_pair_20261103/RUN_PUBLICATION.json](feduba_fixed10_pair_20261103/RUN_PUBLICATION.json)
- [research/feduba_fixed10_pair_20261103/LOCAL_LAUNCH_ONCE.json](feduba_fixed10_pair_20261103/LOCAL_LAUNCH_ONCE.json)
- [research/feduba_fixed10_pair_20261103/LOCAL_LAUNCH_RESULT.json](feduba_fixed10_pair_20261103/LOCAL_LAUNCH_RESULT.json)
- [research/feduba_fixed10_pair_20261103/RUNNING_OBSERVATION.json](feduba_fixed10_pair_20261103/RUNNING_OBSERVATION.json)
- [research/feduba_fixed10_pair_20261103/RUNNING_REPORT_KO.txt](feduba_fixed10_pair_20261103/RUNNING_REPORT_KO.txt)
- [research/feduba_fixed10_pair_20261103/observe_status_v2.py](feduba_fixed10_pair_20261103/observe_status_v2.py)
- [research/feduba_fixed10_pair_20261103/MONITOR_PROTOCOL_V2.txt](feduba_fixed10_pair_20261103/MONITOR_PROTOCOL_V2.txt)
- [research/feduba_fixed10_pair_20261103/MONITOR_FREEZE_V2.json](feduba_fixed10_pair_20261103/MONITOR_FREEZE_V2.json)
- [research/feduba_fixed10_pair_20261103/MONITOR_TRANSPORT_FAILURE_OBSERVATION.json](feduba_fixed10_pair_20261103/MONITOR_TRANSPORT_FAILURE_OBSERVATION.json)
- [research/feduba_fixed10_pair_20261103/FU_benign_RESULT.json](feduba_fixed10_pair_20261103/FU_benign_RESULT.json)
- [research/feduba_fixed10_pair_20261103/FU_benign_STATE.json](feduba_fixed10_pair_20261103/FU_benign_STATE.json)
- [research/feduba_fixed10_pair_20261103/BENIGN_TRAINING_COMPLETION_SUMMARY.json](feduba_fixed10_pair_20261103/BENIGN_TRAINING_COMPLETION_SUMMARY.json)
- [research/feduba_fixed10_pair_20261103/BENIGN_TRAINING_COMPLETION_OBSERVATION.json](feduba_fixed10_pair_20261103/BENIGN_TRAINING_COMPLETION_OBSERVATION.json)
- [research/feduba_fixed10_pair_20261103/BENIGN_TRAINING_COMPLETION_REPORT_KO.txt](feduba_fixed10_pair_20261103/BENIGN_TRAINING_COMPLETION_REPORT_KO.txt)
- [research/feduba_fixed10_pair_20261103/FU_benign_VERIFIED.json](feduba_fixed10_pair_20261103/FU_benign_VERIFIED.json)
- [research/feduba_fixed10_pair_20261103/BENIGN_AUDIT_COMPLETION_SUMMARY.json](feduba_fixed10_pair_20261103/BENIGN_AUDIT_COMPLETION_SUMMARY.json)
- [research/feduba_fixed10_pair_20261103/BENIGN_AUDIT_COMPLETION_OBSERVATION.json](feduba_fixed10_pair_20261103/BENIGN_AUDIT_COMPLETION_OBSERVATION.json)
- [research/feduba_fixed10_pair_20261103/BENIGN_AUDIT_COMPLETION_REPORT_KO.txt](feduba_fixed10_pair_20261103/BENIGN_AUDIT_COMPLETION_REPORT_KO.txt)
- [research/feduba_fixed10_pair_20261103/FU_attack_RESULT.json](feduba_fixed10_pair_20261103/FU_attack_RESULT.json)
- [research/feduba_fixed10_pair_20261103/FU_attack_STATE.json](feduba_fixed10_pair_20261103/FU_attack_STATE.json)
- [research/feduba_fixed10_pair_20261103/FU_attack_VERIFIED.json](feduba_fixed10_pair_20261103/FU_attack_VERIFIED.json)
- [research/feduba_fixed10_pair_20261103/PAIR_EVAL_RESULT.json](feduba_fixed10_pair_20261103/PAIR_EVAL_RESULT.json)
- [research/feduba_fixed10_pair_20261103/PAIR_EVAL_VERIFIED.json](feduba_fixed10_pair_20261103/PAIR_EVAL_VERIFIED.json)
- [research/feduba_fixed10_pair_20261103/COMPLETION.json](feduba_fixed10_pair_20261103/COMPLETION.json)
- [research/feduba_fixed10_pair_20261103/REMOTE_CHECKPOINT_REVIEW.json](feduba_fixed10_pair_20261103/REMOTE_CHECKPOINT_REVIEW.json)
- [research/feduba_fixed10_pair_20261103/CONTROLLER_STATE.json](feduba_fixed10_pair_20261103/CONTROLLER_STATE.json)
- [research/feduba_fixed10_pair_20261103/FINAL_TERMINAL_OBSERVATION.json](feduba_fixed10_pair_20261103/FINAL_TERMINAL_OBSERVATION.json)
- [research/feduba_fixed10_pair_20261103/FINAL_RESULT_SUMMARY.json](feduba_fixed10_pair_20261103/FINAL_RESULT_SUMMARY.json)
- [research/feduba_fixed10_pair_20261103/FINAL_REPORT_KO.txt](feduba_fixed10_pair_20261103/FINAL_REPORT_KO.txt)
- [research/feduba_fixed10_pair_20261103/PAPER_COMPARISON.txt](feduba_fixed10_pair_20261103/PAPER_COMPARISON.txt)
- [research/feduba_fixed10_pair_20261103/NEXT_STAGE_RATIONALE.txt](feduba_fixed10_pair_20261103/NEXT_STAGE_RATIONALE.txt)
- [research/feduba_fixed10_pair_20261103/EVALUATOR_ROUTE_DIFFERENCE.json](feduba_fixed10_pair_20261103/EVALUATOR_ROUTE_DIFFERENCE.json)
- [research/feduba_author_archive_review_20261103/PROTOCOL.txt](feduba_author_archive_review_20261103/PROTOCOL.txt)
- [research/feduba_author_archive_review_20261103/REVIEW_PROFILE.json](feduba_author_archive_review_20261103/REVIEW_PROFILE.json)
- [research/feduba_author_archive_review_20261103/SOURCE_DISCOVERY.json](feduba_author_archive_review_20261103/SOURCE_DISCOVERY.json)
- [research/feduba_author_archive_review_20261103/inspect_archive.py](feduba_author_archive_review_20261103/inspect_archive.py)
- [research/feduba_author_archive_review_20261103/SOURCE_FREEZE.json](feduba_author_archive_review_20261103/SOURCE_FREEZE.json)
- [research/feduba_author_archive_review_20261103/PACKAGING_RECOVERY_PROTOCOL.txt](feduba_author_archive_review_20261103/PACKAGING_RECOVERY_PROTOCOL.txt)
- [research/feduba_author_archive_review_20261103/RECOVERY_PROFILE.json](feduba_author_archive_review_20261103/RECOVERY_PROFILE.json)
- [research/feduba_author_archive_review_20261103/inspect_archive_v2.py](feduba_author_archive_review_20261103/inspect_archive_v2.py)
- [research/feduba_author_archive_review_20261103/REVIEW_FAILURE.json](feduba_author_archive_review_20261103/REVIEW_FAILURE.json)
- [research/feduba_author_archive_review_20261103/REVIEW_ONCE.json](feduba_author_archive_review_20261103/REVIEW_ONCE.json)
- [research/feduba_author_archive_review_20261103/SOURCE_PUBLICATION.json](feduba_author_archive_review_20261103/SOURCE_PUBLICATION.json)
- [research/feduba_author_archive_review_20261103/SOURCE_FREEZE_V2.json](feduba_author_archive_review_20261103/SOURCE_FREEZE_V2.json)
- [research/feduba_author_archive_review_20261103/SOURCE_PUBLICATION_V2.json](feduba_author_archive_review_20261103/SOURCE_PUBLICATION_V2.json)
- [research/feduba_author_archive_review_20261103/REVIEW_RECOVERY_ONCE.json](feduba_author_archive_review_20261103/REVIEW_RECOVERY_ONCE.json)
- [research/feduba_author_archive_review_20261103/REVIEW_RECOVERY_RESULT.json](feduba_author_archive_review_20261103/REVIEW_RECOVERY_RESULT.json)
- [research/feduba_author_archive_review_20261103/REPORT_KO.txt](feduba_author_archive_review_20261103/REPORT_KO.txt)
- [research/feduba_author_archive_review_20261103/COMPLETION_SUMMARY.json](feduba_author_archive_review_20261103/COMPLETION_SUMMARY.json)
- [research/feduba_author_archive_review_20261103/LOCAL_READBACK_FAILURE_OBSERVATION.json](feduba_author_archive_review_20261103/LOCAL_READBACK_FAILURE_OBSERVATION.json)
- [research/feduba_author_archive_review_20261103/METADATA_READBACK_PROTOCOL.txt](feduba_author_archive_review_20261103/METADATA_READBACK_PROTOCOL.txt)
- [research/feduba_author_archive_review_20261103/FINAL_METADATA_CHECK.json](feduba_author_archive_review_20261103/FINAL_METADATA_CHECK.json)
- [research/feduba_fixed10_sss_direction_diagnosis_20261103/PROFILE.json](feduba_fixed10_sss_direction_diagnosis_20261103/PROFILE.json)
- [research/feduba_fixed10_sss_direction_diagnosis_20261103/INPUT_BINDING.json](feduba_fixed10_sss_direction_diagnosis_20261103/INPUT_BINDING.json)
- [research/feduba_fixed10_sss_direction_diagnosis_20261103/PROTOCOL.txt](feduba_fixed10_sss_direction_diagnosis_20261103/PROTOCOL.txt)
- [research/feduba_fixed10_sss_direction_diagnosis_20261103/native_memory.py](feduba_fixed10_sss_direction_diagnosis_20261103/native_memory.py)
- [research/feduba_fixed10_sss_direction_diagnosis_20261103/native_processes.py](feduba_fixed10_sss_direction_diagnosis_20261103/native_processes.py)
- [research/feduba_fixed10_sss_direction_diagnosis_20261103/common.py](feduba_fixed10_sss_direction_diagnosis_20261103/common.py)
- [research/feduba_fixed10_sss_direction_diagnosis_20261103/derive_direction.py](feduba_fixed10_sss_direction_diagnosis_20261103/derive_direction.py)
- [research/feduba_fixed10_sss_direction_diagnosis_20261103/verify_direction.py](feduba_fixed10_sss_direction_diagnosis_20261103/verify_direction.py)
- [research/feduba_fixed10_sss_direction_diagnosis_20261103/controller.py](feduba_fixed10_sss_direction_diagnosis_20261103/controller.py)
- [research/feduba_fixed10_sss_direction_diagnosis_20261103/SOURCE_FREEZE.json](feduba_fixed10_sss_direction_diagnosis_20261103/SOURCE_FREEZE.json)
- [research/feduba_fixed10_sss_direction_diagnosis_20261103/SOURCE_PUBLICATION.json](feduba_fixed10_sss_direction_diagnosis_20261103/SOURCE_PUBLICATION.json)
- [research/feduba_fixed10_sss_direction_diagnosis_20261103/LOCAL_FOREGROUND_ONCE.json](feduba_fixed10_sss_direction_diagnosis_20261103/LOCAL_FOREGROUND_ONCE.json)
- [research/feduba_fixed10_sss_direction_diagnosis_20261103/LOCAL_READBACK.json](feduba_fixed10_sss_direction_diagnosis_20261103/LOCAL_READBACK.json)
- [research/feduba_fixed10_sss_direction_diagnosis_20261103/CONTROLLER_ONCE.json](feduba_fixed10_sss_direction_diagnosis_20261103/CONTROLLER_ONCE.json)
- [research/feduba_fixed10_sss_direction_diagnosis_20261103/PRIMARY_ONCE.json](feduba_fixed10_sss_direction_diagnosis_20261103/PRIMARY_ONCE.json)
- [research/feduba_fixed10_sss_direction_diagnosis_20261103/VERIFY_ONCE.json](feduba_fixed10_sss_direction_diagnosis_20261103/VERIFY_ONCE.json)
- [research/feduba_fixed10_sss_direction_diagnosis_20261103/STATE.json](feduba_fixed10_sss_direction_diagnosis_20261103/STATE.json)
- [research/feduba_fixed10_sss_direction_diagnosis_20261103/RESULT.json](feduba_fixed10_sss_direction_diagnosis_20261103/RESULT.json)
- [research/feduba_fixed10_sss_direction_diagnosis_20261103/VERIFIED.json](feduba_fixed10_sss_direction_diagnosis_20261103/VERIFIED.json)
- [research/feduba_fixed10_sss_direction_diagnosis_20261103/COMPLETION.json](feduba_fixed10_sss_direction_diagnosis_20261103/COMPLETION.json)
- [research/feduba_fixed10_sss_direction_diagnosis_20261103/TERMINAL_OBSERVATION.json](feduba_fixed10_sss_direction_diagnosis_20261103/TERMINAL_OBSERVATION.json)
- [research/feduba_fixed10_sss_direction_diagnosis_20261103/REPORT_KO.txt](feduba_fixed10_sss_direction_diagnosis_20261103/REPORT_KO.txt)
- [research/feduba_fixed10_sss_direction_diagnosis_20261103/NEXT_STAGE_RATIONALE.txt](feduba_fixed10_sss_direction_diagnosis_20261103/NEXT_STAGE_RATIONALE.txt)
- [research/feduba_related_helper_positive_20261103/.gitignore](feduba_related_helper_positive_20261103/.gitignore)
- [research/feduba_related_helper_positive_20261103/CLEAN_FL_PROFILE.json](feduba_related_helper_positive_20261103/CLEAN_FL_PROFILE.json)
- [research/feduba_related_helper_positive_20261103/CLEAN_FL_READY.json](feduba_related_helper_positive_20261103/CLEAN_FL_READY.json)
- [research/feduba_related_helper_positive_20261103/CLEAN_FL_RESULT.json](feduba_related_helper_positive_20261103/CLEAN_FL_RESULT.json)
- [research/feduba_related_helper_positive_20261103/CLEAN_FL_VERIFIED.json](feduba_related_helper_positive_20261103/CLEAN_FL_VERIFIED.json)
- [research/feduba_related_helper_positive_20261103/COPY_PROVENANCE.json](feduba_related_helper_positive_20261103/COPY_PROVENANCE.json)
- [research/feduba_related_helper_positive_20261103/FOUNDATION_INPUT_BINDING.json](feduba_related_helper_positive_20261103/FOUNDATION_INPUT_BINDING.json)
- [research/feduba_related_helper_positive_20261103/FU_ENGINE_CPU_RESULT.json](feduba_related_helper_positive_20261103/FU_ENGINE_CPU_RESULT.json)
- [research/feduba_related_helper_positive_20261103/FU_POLICY_CPU_RESULT.json](feduba_related_helper_positive_20261103/FU_POLICY_CPU_RESULT.json)
- [research/feduba_related_helper_positive_20261103/FU_PROFILE.json](feduba_related_helper_positive_20261103/FU_PROFILE.json)
- [research/feduba_related_helper_positive_20261103/GPU_PREFLIGHT_RESULT.json](feduba_related_helper_positive_20261103/GPU_PREFLIGHT_RESULT.json)
- [research/feduba_related_helper_positive_20261103/MONITOR_PROTOCOL.txt](feduba_related_helper_positive_20261103/MONITOR_PROTOCOL.txt)
- [research/feduba_related_helper_positive_20261103/PROTOCOL.txt](feduba_related_helper_positive_20261103/PROTOCOL.txt)
- [research/feduba_related_helper_positive_20261103/REPORT_KO.txt](feduba_related_helper_positive_20261103/REPORT_KO.txt)
- [research/feduba_related_helper_positive_20261103/SIGN_CONTRACT_PROFILE.json](feduba_related_helper_positive_20261103/SIGN_CONTRACT_PROFILE.json)
- [research/feduba_related_helper_positive_20261103/SIGN_SOURCE_EVIDENCE.json](feduba_related_helper_positive_20261103/SIGN_SOURCE_EVIDENCE.json)
- [research/feduba_related_helper_positive_20261103/SOURCE_PROFILE.json](feduba_related_helper_positive_20261103/SOURCE_PROFILE.json)
- [research/feduba_related_helper_positive_20261103/SSS_REPLAY_COUNT_BINDING.json](feduba_related_helper_positive_20261103/SSS_REPLAY_COUNT_BINDING.json)
- [research/feduba_related_helper_positive_20261103/TRIGGER_SOURCE_BINDING.json](feduba_related_helper_positive_20261103/TRIGGER_SOURCE_BINDING.json)
- [research/feduba_related_helper_positive_20261103/controller.py](feduba_related_helper_positive_20261103/controller.py)
- [research/feduba_related_helper_positive_20261103/core.py](feduba_related_helper_positive_20261103/core.py)
- [research/feduba_related_helper_positive_20261103/fu_core.py](feduba_related_helper_positive_20261103/fu_core.py)
- [research/feduba_related_helper_positive_20261103/fu_runner.py](feduba_related_helper_positive_20261103/fu_runner.py)
- [research/feduba_related_helper_positive_20261103/fu_training.py](feduba_related_helper_positive_20261103/fu_training.py)
- [research/feduba_related_helper_positive_20261103/launch_once.ps1](feduba_related_helper_positive_20261103/launch_once.ps1)
- [research/feduba_related_helper_positive_20261103/launch_via_ssh_once.py](feduba_related_helper_positive_20261103/launch_via_ssh_once.py)
- [research/feduba_related_helper_positive_20261103/model_reference.py](feduba_related_helper_positive_20261103/model_reference.py)
- [research/feduba_related_helper_positive_20261103/native_memory.py](feduba_related_helper_positive_20261103/native_memory.py)
- [research/feduba_related_helper_positive_20261103/native_processes.py](feduba_related_helper_positive_20261103/native_processes.py)
- [research/feduba_related_helper_positive_20261103/observe_status.py](feduba_related_helper_positive_20261103/observe_status.py)
- [research/feduba_related_helper_positive_20261103/pair_binding.py](feduba_related_helper_positive_20261103/pair_binding.py)
- [research/feduba_related_helper_positive_20261103/prepare_run.py](feduba_related_helper_positive_20261103/prepare_run.py)
- [research/feduba_related_helper_positive_20261103/prepare_via_ssh_once.py](feduba_related_helper_positive_20261103/prepare_via_ssh_once.py)
- [research/feduba_related_helper_positive_20261103/runtime_common.py](feduba_related_helper_positive_20261103/runtime_common.py)
- [research/feduba_related_helper_positive_20261103/sign_contract.py](feduba_related_helper_positive_20261103/sign_contract.py)
- [research/feduba_related_helper_positive_20261103/source_review.py](feduba_related_helper_positive_20261103/source_review.py)
- [research/feduba_related_helper_positive_20261103/trigger_binding.py](feduba_related_helper_positive_20261103/trigger_binding.py)
- [research/feduba_related_helper_positive_20261103/verify_fu.py](feduba_related_helper_positive_20261103/verify_fu.py)
- [research/feduba_related_helper_positive_20261103/SOURCE_FREEZE.json](feduba_related_helper_positive_20261103/SOURCE_FREEZE.json)
- [research/feduba_related_helper_positive_20261103/SOURCE_PUBLICATION.json](feduba_related_helper_positive_20261103/SOURCE_PUBLICATION.json)
- [research/feduba_related_helper_positive_20261103/SOURCE_REVIEW_RESULT.json](feduba_related_helper_positive_20261103/SOURCE_REVIEW_RESULT.json)
- [research/feduba_related_helper_positive_20261103/SIGN_CONTRACT_ONCE.json](feduba_related_helper_positive_20261103/SIGN_CONTRACT_ONCE.json)
- [research/feduba_related_helper_positive_20261103/SIGN_CONTRACT_RESULT.json](feduba_related_helper_positive_20261103/SIGN_CONTRACT_RESULT.json)
- [research/feduba_related_helper_positive_20261103/UPSTREAM_TERMINAL_CHECK.json](feduba_related_helper_positive_20261103/UPSTREAM_TERMINAL_CHECK.json)
- [research/feduba_related_helper_positive_20261103/PREPARE_ONCE.json](feduba_related_helper_positive_20261103/PREPARE_ONCE.json)
- [research/feduba_related_helper_positive_20261103/BASELINE_INPUT_BINDING.json](feduba_related_helper_positive_20261103/BASELINE_INPUT_BINDING.json)
- [research/feduba_related_helper_positive_20261103/FU_LAUNCH_PROFILE.json](feduba_related_helper_positive_20261103/FU_LAUNCH_PROFILE.json)
- [research/feduba_related_helper_positive_20261103/LAUNCH_PROFILE.json](feduba_related_helper_positive_20261103/LAUNCH_PROFILE.json)
- [research/feduba_related_helper_positive_20261103/PREPARATION_RESULT.json](feduba_related_helper_positive_20261103/PREPARATION_RESULT.json)
- [research/feduba_related_helper_positive_20261103/RUN_FREEZE.json](feduba_related_helper_positive_20261103/RUN_FREEZE.json)
- [research/feduba_related_helper_positive_20261103/FU_RUN_FREEZE.json](feduba_related_helper_positive_20261103/FU_RUN_FREEZE.json)
- [research/feduba_related_helper_positive_20261103/ACTUAL_RUN_REPORT_KO.txt](feduba_related_helper_positive_20261103/ACTUAL_RUN_REPORT_KO.txt)
- [research/feduba_related_helper_positive_20261103/.gitattributes](feduba_related_helper_positive_20261103/.gitattributes)
- [research/feduba_related_helper_positive_20261103/PUBLICATION_BYTE_MISMATCH_OBSERVATION.json](feduba_related_helper_positive_20261103/PUBLICATION_BYTE_MISMATCH_OBSERVATION.json)
- [research/feduba_related_helper_positive_20261103/PUBLICATION_BYTE_PRESERVATION_PROTOCOL.txt](feduba_related_helper_positive_20261103/PUBLICATION_BYTE_PRESERVATION_PROTOCOL.txt)
- [research/feduba_related_helper_positive_20261103/RUN_PUBLICATION.json](feduba_related_helper_positive_20261103/RUN_PUBLICATION.json)
- [research/feduba_related_helper_positive_20261103/PUBLIC_BYTE_EXPECTATIONS.json](feduba_related_helper_positive_20261103/PUBLIC_BYTE_EXPECTATIONS.json)
- [research/feduba_related_helper_positive_20261103/PUBLICATION_BYTE_CHECKS.json](feduba_related_helper_positive_20261103/PUBLICATION_BYTE_CHECKS.json)
- [research/feduba_related_helper_positive_20261103/PUBLICATION_BYTE_COUNT_NOTE.json](feduba_related_helper_positive_20261103/PUBLICATION_BYTE_COUNT_NOTE.json)
- [research/feduba_related_helper_positive_20261103/RUNNING_OBSERVATION.json](feduba_related_helper_positive_20261103/RUNNING_OBSERVATION.json)
- [research/feduba_related_helper_positive_20261103/RUNNING_REPORT_KO.txt](feduba_related_helper_positive_20261103/RUNNING_REPORT_KO.txt)
- [research/feduba_related_helper_positive_evaluation_20261103/.gitattributes](feduba_related_helper_positive_evaluation_20261103/.gitattributes)
- [research/feduba_related_helper_positive_evaluation_20261103/.gitignore](feduba_related_helper_positive_evaluation_20261103/.gitignore)
- [research/feduba_related_helper_positive_evaluation_20261103/CLEAN_FL_PROFILE.json](feduba_related_helper_positive_evaluation_20261103/CLEAN_FL_PROFILE.json)
- [research/feduba_related_helper_positive_evaluation_20261103/CLEAN_FL_READY.json](feduba_related_helper_positive_evaluation_20261103/CLEAN_FL_READY.json)
- [research/feduba_related_helper_positive_evaluation_20261103/COPY_PROVENANCE.json](feduba_related_helper_positive_evaluation_20261103/COPY_PROVENANCE.json)
- [research/feduba_related_helper_positive_evaluation_20261103/EVAL_PROFILE.json](feduba_related_helper_positive_evaluation_20261103/EVAL_PROFILE.json)
- [research/feduba_related_helper_positive_evaluation_20261103/FU_PROFILE.json](feduba_related_helper_positive_evaluation_20261103/FU_PROFILE.json)
- [research/feduba_related_helper_positive_evaluation_20261103/GPU_PREFLIGHT_RESULT.json](feduba_related_helper_positive_evaluation_20261103/GPU_PREFLIGHT_RESULT.json)
- [research/feduba_related_helper_positive_evaluation_20261103/MONITOR_PROTOCOL.txt](feduba_related_helper_positive_evaluation_20261103/MONITOR_PROTOCOL.txt)
- [research/feduba_related_helper_positive_evaluation_20261103/PAIR_EVAL_CPU_RESULT.json](feduba_related_helper_positive_evaluation_20261103/PAIR_EVAL_CPU_RESULT.json)
- [research/feduba_related_helper_positive_evaluation_20261103/PROTOCOL.txt](feduba_related_helper_positive_evaluation_20261103/PROTOCOL.txt)
- [research/feduba_related_helper_positive_evaluation_20261103/REPORT_KO.txt](feduba_related_helper_positive_evaluation_20261103/REPORT_KO.txt)
- [research/feduba_related_helper_positive_evaluation_20261103/SOURCE_PROFILE.json](feduba_related_helper_positive_evaluation_20261103/SOURCE_PROFILE.json)
- [research/feduba_related_helper_positive_evaluation_20261103/TRIGGER_SOURCE_BINDING.json](feduba_related_helper_positive_evaluation_20261103/TRIGGER_SOURCE_BINDING.json)
- [research/feduba_related_helper_positive_evaluation_20261103/controller.py](feduba_related_helper_positive_evaluation_20261103/controller.py)
- [research/feduba_related_helper_positive_evaluation_20261103/eval_binding.py](feduba_related_helper_positive_evaluation_20261103/eval_binding.py)
- [research/feduba_related_helper_positive_evaluation_20261103/evaluate_pair.py](feduba_related_helper_positive_evaluation_20261103/evaluate_pair.py)
- [research/feduba_related_helper_positive_evaluation_20261103/export_review.py](feduba_related_helper_positive_evaluation_20261103/export_review.py)
- [research/feduba_related_helper_positive_evaluation_20261103/launch_once.ps1](feduba_related_helper_positive_evaluation_20261103/launch_once.ps1)
- [research/feduba_related_helper_positive_evaluation_20261103/launch_via_ssh_once.py](feduba_related_helper_positive_evaluation_20261103/launch_via_ssh_once.py)
- [research/feduba_related_helper_positive_evaluation_20261103/model_reference.py](feduba_related_helper_positive_evaluation_20261103/model_reference.py)
- [research/feduba_related_helper_positive_evaluation_20261103/native_memory.py](feduba_related_helper_positive_evaluation_20261103/native_memory.py)
- [research/feduba_related_helper_positive_evaluation_20261103/native_processes.py](feduba_related_helper_positive_evaluation_20261103/native_processes.py)
- [research/feduba_related_helper_positive_evaluation_20261103/observe_status.py](feduba_related_helper_positive_evaluation_20261103/observe_status.py)
- [research/feduba_related_helper_positive_evaluation_20261103/pair_binding.py](feduba_related_helper_positive_evaluation_20261103/pair_binding.py)
- [research/feduba_related_helper_positive_evaluation_20261103/pair_eval_core.py](feduba_related_helper_positive_evaluation_20261103/pair_eval_core.py)
- [research/feduba_related_helper_positive_evaluation_20261103/prepare_eval.py](feduba_related_helper_positive_evaluation_20261103/prepare_eval.py)
- [research/feduba_related_helper_positive_evaluation_20261103/prepare_via_ssh_once.py](feduba_related_helper_positive_evaluation_20261103/prepare_via_ssh_once.py)
- [research/feduba_related_helper_positive_evaluation_20261103/runtime_common.py](feduba_related_helper_positive_evaluation_20261103/runtime_common.py)
- [research/feduba_related_helper_positive_evaluation_20261103/source_review.py](feduba_related_helper_positive_evaluation_20261103/source_review.py)
- [research/feduba_related_helper_positive_evaluation_20261103/trigger_binding.py](feduba_related_helper_positive_evaluation_20261103/trigger_binding.py)
- [research/feduba_related_helper_positive_evaluation_20261103/verify_pair_evaluation.py](feduba_related_helper_positive_evaluation_20261103/verify_pair_evaluation.py)
- [research/feduba_related_helper_positive_evaluation_20261103/SOURCE_FREEZE.json](feduba_related_helper_positive_evaluation_20261103/SOURCE_FREEZE.json)
- [research/feduba_related_helper_positive_evaluation_20261103/SOURCE_PUBLICATION.json](feduba_related_helper_positive_evaluation_20261103/SOURCE_PUBLICATION.json)
- [research/feduba_related_helper_positive_evaluation_20261103/SOURCE_REVIEW_RESULT.json](feduba_related_helper_positive_evaluation_20261103/SOURCE_REVIEW_RESULT.json)
- [research/feduba_related_helper_positive_evaluation_20261103/SOURCE_REVIEW_REPORT_KO.txt](feduba_related_helper_positive_evaluation_20261103/SOURCE_REVIEW_REPORT_KO.txt)
- [research/feduba_related_helper_positive_20261103/FU_attack_RESULT.json](feduba_related_helper_positive_20261103/FU_attack_RESULT.json)
- [research/feduba_related_helper_positive_20261103/FU_attack_VERIFIED.json](feduba_related_helper_positive_20261103/FU_attack_VERIFIED.json)
- [research/feduba_related_helper_positive_20261103/COMPLETION.json](feduba_related_helper_positive_20261103/COMPLETION.json)
- [research/feduba_related_helper_positive_20261103/CPU_COMPLETION_OBSERVATION.json](feduba_related_helper_positive_20261103/CPU_COMPLETION_OBSERVATION.json)
- [research/feduba_related_helper_positive_20261103/CPU_COMPLETION_SUMMARY.json](feduba_related_helper_positive_20261103/CPU_COMPLETION_SUMMARY.json)
- [research/feduba_related_helper_positive_20261103/CPU_COMPLETION_REPORT_KO.txt](feduba_related_helper_positive_20261103/CPU_COMPLETION_REPORT_KO.txt)
- [research/feduba_related_helper_positive_evaluation_20261103/PREPARE_ONCE.json](feduba_related_helper_positive_evaluation_20261103/PREPARE_ONCE.json)
- [research/feduba_related_helper_positive_evaluation_20261103/UPSTREAM_TERMINAL_CHECK.json](feduba_related_helper_positive_evaluation_20261103/UPSTREAM_TERMINAL_CHECK.json)
- [research/feduba_related_helper_positive_evaluation_20261103/INPUT_BINDING.json](feduba_related_helper_positive_evaluation_20261103/INPUT_BINDING.json)
- [research/feduba_related_helper_positive_evaluation_20261103/EVAL_LAUNCH_PROFILE.json](feduba_related_helper_positive_evaluation_20261103/EVAL_LAUNCH_PROFILE.json)
- [research/feduba_related_helper_positive_evaluation_20261103/PREPARATION_RESULT.json](feduba_related_helper_positive_evaluation_20261103/PREPARATION_RESULT.json)
- [research/feduba_related_helper_positive_evaluation_20261103/EVAL_RUN_FREEZE.json](feduba_related_helper_positive_evaluation_20261103/EVAL_RUN_FREEZE.json)
- [research/feduba_related_helper_positive_evaluation_20261103/ACTUAL_EVALUATION_REPORT_KO.txt](feduba_related_helper_positive_evaluation_20261103/ACTUAL_EVALUATION_REPORT_KO.txt)
- [research/feduba_related_helper_positive_evaluation_20261103/RUN_PUBLICATION.json](feduba_related_helper_positive_evaluation_20261103/RUN_PUBLICATION.json)
- [research/feduba_related_helper_positive_evaluation_20261103/PUBLIC_BYTE_EXPECTATIONS.json](feduba_related_helper_positive_evaluation_20261103/PUBLIC_BYTE_EXPECTATIONS.json)
- [research/feduba_related_helper_positive_evaluation_20261103/PUBLICATION_BYTE_CHECKS.json](feduba_related_helper_positive_evaluation_20261103/PUBLICATION_BYTE_CHECKS.json)
- [research/feduba_related_helper_positive_evaluation_20261103/LOCAL_LAUNCH_FAILURE.json](feduba_related_helper_positive_evaluation_20261103/LOCAL_LAUNCH_FAILURE.json)
- [research/feduba_related_helper_positive_evaluation_20261103/LAUNCH_TRANSPORT_RECOVERY_PROTOCOL.txt](feduba_related_helper_positive_evaluation_20261103/LAUNCH_TRANSPORT_RECOVERY_PROTOCOL.txt)
- [research/feduba_related_helper_positive_evaluation_20261103/PRE_SSH_LAUNCH_FAILURE_OBSERVATION.json](feduba_related_helper_positive_evaluation_20261103/PRE_SSH_LAUNCH_FAILURE_OBSERVATION.json)
- [research/feduba_related_helper_positive_evaluation_20261103/LAUNCH_TRANSPORT_RECOVERY_PROFILE.json](feduba_related_helper_positive_evaluation_20261103/LAUNCH_TRANSPORT_RECOVERY_PROFILE.json)
- [research/feduba_related_helper_positive_evaluation_20261103/launch_transport_recovery_once.py](feduba_related_helper_positive_evaluation_20261103/launch_transport_recovery_once.py)
- [research/feduba_related_helper_positive_evaluation_20261103/LAUNCH_TRANSPORT_RECOVERY_FREEZE.json](feduba_related_helper_positive_evaluation_20261103/LAUNCH_TRANSPORT_RECOVERY_FREEZE.json)
- [research/feduba_related_helper_positive_evaluation_20261103/PAIR_EVAL_RESULT.json](feduba_related_helper_positive_evaluation_20261103/PAIR_EVAL_RESULT.json)
- [research/feduba_related_helper_positive_evaluation_20261103/PAIR_EVAL_AUDIT_FAILURE.json](feduba_related_helper_positive_evaluation_20261103/PAIR_EVAL_AUDIT_FAILURE.json)
- [research/feduba_related_helper_positive_evaluation_20261103/PAIR_EVAL_AUDIT_STATE.json](feduba_related_helper_positive_evaluation_20261103/PAIR_EVAL_AUDIT_STATE.json)
- [research/feduba_related_helper_positive_evaluation_20261103/CONTROLLER_FAILURE.json](feduba_related_helper_positive_evaluation_20261103/CONTROLLER_FAILURE.json)
- [research/feduba_related_helper_positive_evaluation_20261103/CONTROLLER_STATE.json](feduba_related_helper_positive_evaluation_20261103/CONTROLLER_STATE.json)
- [research/feduba_related_helper_positive_evaluation_20261103/PAIR_EVAL_ONCE.json](feduba_related_helper_positive_evaluation_20261103/PAIR_EVAL_ONCE.json)
- [research/feduba_related_helper_positive_evaluation_20261103/PAIR_EVAL_AUDIT_ONCE.json](feduba_related_helper_positive_evaluation_20261103/PAIR_EVAL_AUDIT_ONCE.json)
- [research/feduba_related_helper_positive_evaluation_20261103/FAILED_EVALUATION_TERMINAL_OBSERVATION.json](feduba_related_helper_positive_evaluation_20261103/FAILED_EVALUATION_TERMINAL_OBSERVATION.json)
- [research/feduba_related_helper_positive_evaluation_20261103/LAUNCH_TRANSPORT_RECOVERY_PUBLICATION.json](feduba_related_helper_positive_evaluation_20261103/LAUNCH_TRANSPORT_RECOVERY_PUBLICATION.json)
- [research/feduba_related_helper_positive_evaluation_20261103/LOCAL_TRANSPORT_RECOVERY_ONCE.json](feduba_related_helper_positive_evaluation_20261103/LOCAL_TRANSPORT_RECOVERY_ONCE.json)
- [research/feduba_related_helper_positive_evaluation_20261103/LOCAL_TRANSPORT_RECOVERY_RESULT.json](feduba_related_helper_positive_evaluation_20261103/LOCAL_TRANSPORT_RECOVERY_RESULT.json)
- [research/feduba_positive_evaluation_prefix_archive_20261103/.gitattributes](feduba_positive_evaluation_prefix_archive_20261103/.gitattributes)
- [research/feduba_positive_evaluation_prefix_archive_20261103/.gitignore](feduba_positive_evaluation_prefix_archive_20261103/.gitignore)
- [research/feduba_positive_evaluation_prefix_archive_20261103/FAILED_EVALUATION_TERMINAL_OBSERVATION.json](feduba_positive_evaluation_prefix_archive_20261103/FAILED_EVALUATION_TERMINAL_OBSERVATION.json)
- [research/feduba_positive_evaluation_prefix_archive_20261103/PROFILE.json](feduba_positive_evaluation_prefix_archive_20261103/PROFILE.json)
- [research/feduba_positive_evaluation_prefix_archive_20261103/PROTOCOL.txt](feduba_positive_evaluation_prefix_archive_20261103/PROTOCOL.txt)
- [research/feduba_positive_evaluation_prefix_archive_20261103/REPORT_KO.txt](feduba_positive_evaluation_prefix_archive_20261103/REPORT_KO.txt)
- [research/feduba_positive_evaluation_prefix_archive_20261103/binding.py](feduba_positive_evaluation_prefix_archive_20261103/binding.py)
- [research/feduba_positive_evaluation_prefix_archive_20261103/controller.py](feduba_positive_evaluation_prefix_archive_20261103/controller.py)
- [research/feduba_positive_evaluation_prefix_archive_20261103/export_review.py](feduba_positive_evaluation_prefix_archive_20261103/export_review.py)
- [research/feduba_positive_evaluation_prefix_archive_20261103/model_reference.py](feduba_positive_evaluation_prefix_archive_20261103/model_reference.py)
- [research/feduba_positive_evaluation_prefix_archive_20261103/native_memory.py](feduba_positive_evaluation_prefix_archive_20261103/native_memory.py)
- [research/feduba_positive_evaluation_prefix_archive_20261103/native_processes.py](feduba_positive_evaluation_prefix_archive_20261103/native_processes.py)
- [research/feduba_positive_evaluation_prefix_archive_20261103/review_prefix.py](feduba_positive_evaluation_prefix_archive_20261103/review_prefix.py)
- [research/feduba_positive_evaluation_prefix_archive_20261103/runtime_common.py](feduba_positive_evaluation_prefix_archive_20261103/runtime_common.py)
- [research/feduba_positive_evaluation_prefix_archive_20261103/SOURCE_FREEZE.json](feduba_positive_evaluation_prefix_archive_20261103/SOURCE_FREEZE.json)
- [research/feduba_positive_evaluation_prefix_archive_20261103/SOURCE_PUBLICATION.json](feduba_positive_evaluation_prefix_archive_20261103/SOURCE_PUBLICATION.json)
- [research/feduba_positive_evaluation_prefix_archive_20261103/PREFIX_REVIEW_RESULT.json](feduba_positive_evaluation_prefix_archive_20261103/PREFIX_REVIEW_RESULT.json)
- [research/feduba_positive_evaluation_prefix_archive_20261103/REMOTE_CHECKPOINT_REVIEW.json](feduba_positive_evaluation_prefix_archive_20261103/REMOTE_CHECKPOINT_REVIEW.json)
- [research/feduba_positive_evaluation_prefix_archive_20261103/COMPLETION.json](feduba_positive_evaluation_prefix_archive_20261103/COMPLETION.json)
- [research/feduba_positive_evaluation_prefix_archive_20261103/CONTROLLER_ONCE.json](feduba_positive_evaluation_prefix_archive_20261103/CONTROLLER_ONCE.json)
- [research/feduba_positive_evaluation_prefix_archive_20261103/review_prefix.py.STARTED.json](feduba_positive_evaluation_prefix_archive_20261103/review_prefix.py.STARTED.json)
- [research/feduba_positive_evaluation_prefix_archive_20261103/export_review.py.STARTED.json](feduba_positive_evaluation_prefix_archive_20261103/export_review.py.STARTED.json)
- [research/feduba_positive_evaluation_prefix_archive_20261103/LOCAL_PREFIX_LAUNCH_RESULT.json](feduba_positive_evaluation_prefix_archive_20261103/LOCAL_PREFIX_LAUNCH_RESULT.json)
- [research/feduba_positive_evaluation_prefix_archive_20261103/TERMINAL_OBSERVATION.json](feduba_positive_evaluation_prefix_archive_20261103/TERMINAL_OBSERVATION.json)
- [research/feduba_positive_evaluation_prefix_archive_20261103/FINAL_RESULT_SUMMARY.json](feduba_positive_evaluation_prefix_archive_20261103/FINAL_RESULT_SUMMARY.json)
- [research/feduba_positive_evaluation_prefix_archive_20261103/FINAL_REPORT_KO.txt](feduba_positive_evaluation_prefix_archive_20261103/FINAL_REPORT_KO.txt)
- [research/feduba_positive_evaluation_prefix_archive_20261103/COMPARISON.txt](feduba_positive_evaluation_prefix_archive_20261103/COMPARISON.txt)
- [research/feduba_positive_evaluation_prefix_archive_20261103/NEXT_STAGE_RATIONALE.txt](feduba_positive_evaluation_prefix_archive_20261103/NEXT_STAGE_RATIONALE.txt)
- [research/feduba_rng_policy_source_review_20261103/.gitattributes](feduba_rng_policy_source_review_20261103/.gitattributes)
- [research/feduba_rng_policy_source_review_20261103/.gitignore](feduba_rng_policy_source_review_20261103/.gitignore)
- [research/feduba_rng_policy_source_review_20261103/INPUT_BINDING.json](feduba_rng_policy_source_review_20261103/INPUT_BINDING.json)
- [research/feduba_rng_policy_source_review_20261103/PROFILE.json](feduba_rng_policy_source_review_20261103/PROFILE.json)
- [research/feduba_rng_policy_source_review_20261103/PROTOCOL.txt](feduba_rng_policy_source_review_20261103/PROTOCOL.txt)
- [research/feduba_rng_policy_source_review_20261103/REPORT_KO.txt](feduba_rng_policy_source_review_20261103/REPORT_KO.txt)
- [research/feduba_rng_policy_source_review_20261103/review_source.py](feduba_rng_policy_source_review_20261103/review_source.py)
- [research/feduba_rng_policy_source_review_20261103/SOURCE_FREEZE.json](feduba_rng_policy_source_review_20261103/SOURCE_FREEZE.json)
- [research/feduba_rng_policy_source_review_20261103/SOURCE_PUBLICATION.json](feduba_rng_policy_source_review_20261103/SOURCE_PUBLICATION.json)
- [research/feduba_rng_policy_source_review_20261103/ONCE.json](feduba_rng_policy_source_review_20261103/ONCE.json)
- [research/feduba_rng_policy_source_review_20261103/RESULT.json](feduba_rng_policy_source_review_20261103/RESULT.json)
- [research/feduba_rng_policy_source_review_20261103/COMPLETION.json](feduba_rng_policy_source_review_20261103/COMPLETION.json)
- [research/feduba_rng_policy_source_review_20261103/TERMINAL_OBSERVATION.json](feduba_rng_policy_source_review_20261103/TERMINAL_OBSERVATION.json)
- [research/feduba_rng_policy_source_review_20261103/COMPLETION_REPORT_KO.txt](feduba_rng_policy_source_review_20261103/COMPLETION_REPORT_KO.txt)
- [research/feduba_rng_policy_source_review_20261103/NEXT_STAGE_RATIONALE.txt](feduba_rng_policy_source_review_20261103/NEXT_STAGE_RATIONALE.txt)
- [research/feduba_rng_policy_source_review_20261103/LOCAL_MEMORY_READINESS_OBSERVATION.json](feduba_rng_policy_source_review_20261103/LOCAL_MEMORY_READINESS_OBSERVATION.json)
- [research/feduba_positive_independent_recovery_20261103/controller.py](feduba_positive_independent_recovery_20261103/controller.py)
- [research/feduba_positive_independent_recovery_20261103/COPY_PROVENANCE.json](feduba_positive_independent_recovery_20261103/COPY_PROVENANCE.json)
- [research/feduba_positive_independent_recovery_20261103/INPUT_BINDING.json](feduba_positive_independent_recovery_20261103/INPUT_BINDING.json)
- [research/feduba_positive_independent_recovery_20261103/native_memory.py](feduba_positive_independent_recovery_20261103/native_memory.py)
- [research/feduba_positive_independent_recovery_20261103/native_processes.py](feduba_positive_independent_recovery_20261103/native_processes.py)
- [research/feduba_positive_independent_recovery_20261103/PROFILE.json](feduba_positive_independent_recovery_20261103/PROFILE.json)
- [research/feduba_positive_independent_recovery_20261103/PROTOCOL.txt](feduba_positive_independent_recovery_20261103/PROTOCOL.txt)
- [research/feduba_positive_independent_recovery_20261103/recovery_contract.py](feduba_positive_independent_recovery_20261103/recovery_contract.py)
- [research/feduba_positive_independent_recovery_20261103/review_recovery.py](feduba_positive_independent_recovery_20261103/review_recovery.py)
- [research/feduba_positive_independent_recovery_20261103/SOURCE_FREEZE.json](feduba_positive_independent_recovery_20261103/SOURCE_FREEZE.json)
- [research/feduba_positive_independent_recovery_20261103/verify_recovery.py](feduba_positive_independent_recovery_20261103/verify_recovery.py)
- [research/feduba_positive_independent_recovery_20261103/SOURCE_PUBLICATION.json](feduba_positive_independent_recovery_20261103/SOURCE_PUBLICATION.json)
- [research/feduba_positive_independent_recovery_20261103/SOURCE_REVIEW_RESULT.json](feduba_positive_independent_recovery_20261103/SOURCE_REVIEW_RESULT.json)
- [research/feduba_positive_independent_recovery_20261103/UPSTREAM_TERMINAL_CHECK.json](feduba_positive_independent_recovery_20261103/UPSTREAM_TERMINAL_CHECK.json)
- [research/feduba_positive_independent_recovery_20261103/PUBLICATION_BYTE_CHECKS.json](feduba_positive_independent_recovery_20261103/PUBLICATION_BYTE_CHECKS.json)
- [research/feduba_positive_independent_recovery_20261103/RUN_FREEZE.json](feduba_positive_independent_recovery_20261103/RUN_FREEZE.json)
- [research/feduba_positive_independent_recovery_20261103/ACTUAL_RUN_REPORT_KO.txt](feduba_positive_independent_recovery_20261103/ACTUAL_RUN_REPORT_KO.txt)
- [research/feduba_positive_independent_recovery_20261103/RUN_PUBLICATION.json](feduba_positive_independent_recovery_20261103/RUN_PUBLICATION.json)
- [research/feduba_positive_independent_recovery_20261103/SOURCE_REVIEW_ONCE.json](feduba_positive_independent_recovery_20261103/SOURCE_REVIEW_ONCE.json)
- [research/feduba_positive_independent_recovery_20261103/RECOVERY_VERIFIED.json](feduba_positive_independent_recovery_20261103/RECOVERY_VERIFIED.json)
- [research/feduba_positive_independent_recovery_20261103/COMPLETION.json](feduba_positive_independent_recovery_20261103/COMPLETION.json)
- [research/feduba_positive_independent_recovery_20261103/RECOVERY_STATE.json](feduba_positive_independent_recovery_20261103/RECOVERY_STATE.json)
- [research/feduba_positive_independent_recovery_20261103/CONTROLLER_STATE.json](feduba_positive_independent_recovery_20261103/CONTROLLER_STATE.json)
- [research/feduba_positive_independent_recovery_20261103/RECOVERY_ONCE.json](feduba_positive_independent_recovery_20261103/RECOVERY_ONCE.json)
- [research/feduba_positive_independent_recovery_20261103/CONTROLLER_ONCE.json](feduba_positive_independent_recovery_20261103/CONTROLLER_ONCE.json)
- [research/feduba_positive_independent_recovery_20261103/GUARD_STATE.json](feduba_positive_independent_recovery_20261103/GUARD_STATE.json)
- [research/feduba_positive_independent_recovery_20261103/CHILD_EXIT.json](feduba_positive_independent_recovery_20261103/CHILD_EXIT.json)
- [research/feduba_positive_independent_recovery_20261103/TERMINAL_OBSERVATION.json](feduba_positive_independent_recovery_20261103/TERMINAL_OBSERVATION.json)
- [research/feduba_positive_independent_recovery_20261103/FINAL_RESULT_SUMMARY.json](feduba_positive_independent_recovery_20261103/FINAL_RESULT_SUMMARY.json)
- [research/feduba_positive_independent_recovery_20261103/COMPLETION_REPORT_KO.txt](feduba_positive_independent_recovery_20261103/COMPLETION_REPORT_KO.txt)
- [research/feduba_positive_independent_recovery_20261103/NEXT_STAGE_RATIONALE.txt](feduba_positive_independent_recovery_20261103/NEXT_STAGE_RATIONALE.txt)
- [research/feduba_positive_independent_recovery_20261103/FINAL_METADATA_CHECK.json](feduba_positive_independent_recovery_20261103/FINAL_METADATA_CHECK.json)
- [research/feduba_concoct_helper_source_review_20261103/INPUT_BINDING.json](feduba_concoct_helper_source_review_20261103/INPUT_BINDING.json)
- [research/feduba_concoct_helper_source_review_20261103/native_memory.py](feduba_concoct_helper_source_review_20261103/native_memory.py)
- [research/feduba_concoct_helper_source_review_20261103/native_processes.py](feduba_concoct_helper_source_review_20261103/native_processes.py)
- [research/feduba_concoct_helper_source_review_20261103/PROFILE.json](feduba_concoct_helper_source_review_20261103/PROFILE.json)
- [research/feduba_concoct_helper_source_review_20261103/PROTOCOL.txt](feduba_concoct_helper_source_review_20261103/PROTOCOL.txt)
- [research/feduba_concoct_helper_source_review_20261103/review_helper.py](feduba_concoct_helper_source_review_20261103/review_helper.py)
- [research/feduba_concoct_helper_source_review_20261103/SOURCE_FREEZE.json](feduba_concoct_helper_source_review_20261103/SOURCE_FREEZE.json)

**묶은 폴더:** [feduba_reproduction_audit_20261031](feduba_reproduction_audit_20261031) · [feduba_paper_implementation_20261031](feduba_paper_implementation_20261031) · [feduba_stage_diagnosis_20261101](feduba_stage_diagnosis_20261101) · [feduba_mixed_surrogate_20261101](feduba_mixed_surrogate_20261101) · [feduba_mixed_trigger_20261101](feduba_mixed_trigger_20261101) · [feduba_mixed_pair_20261101](feduba_mixed_pair_20261101) · [feduba_mixed_monitor_20261101](feduba_mixed_monitor_20261101) · [feduba_mixed_pair_memory_recovery_20261101](feduba_mixed_pair_memory_recovery_20261101) · [feduba_mixed_attack_resume_20261101](feduba_mixed_attack_resume_20261101) · [feduba_mixed_attack_prefix_guard_v2_20261101](feduba_mixed_attack_prefix_guard_v2_20261101) · [feduba_mixed_attack_recovery_run_20261101](feduba_mixed_attack_recovery_run_20261101) · [feduba_metric_conformance_review_20261101](feduba_metric_conformance_review_20261101) · [feduba_mixed_pair_evaluation_recovery_20261101](feduba_mixed_pair_evaluation_recovery_20261101) · [feduba_mixed_pair_eval_native_v2_20261101](feduba_mixed_pair_eval_native_v2_20261101) · [feduba_mixed_pair_delivery_20261101](feduba_mixed_pair_delivery_20261101) · [feduba_mixed_pair_receive_recovery_20261102](feduba_mixed_pair_receive_recovery_20261102) · [feduba_mixed_pair_receive_recovery_v2_20261102](feduba_mixed_pair_receive_recovery_v2_20261102) · [feduba_mixed_pair_receive_start_20261102](feduba_mixed_pair_receive_start_20261102) · [feduba_stg_conformance_review_20261102](feduba_stg_conformance_review_20261102) · [feduba_public_stg_comparison_20261102](feduba_public_stg_comparison_20261102) · [feduba_semantic_transfer_diagnosis_20261102](feduba_semantic_transfer_diagnosis_20261102) · [feduba_targetclass_pair_20261102](feduba_targetclass_pair_20261102) · [feduba_targetclass_launch_recovery_20261102](feduba_targetclass_launch_recovery_20261102) · [feduba_targetclass_launch_recovery_v2_20261102](feduba_targetclass_launch_recovery_v2_20261102) · [feduba_targetclass_launch_recovery_v3_20261102](feduba_targetclass_launch_recovery_v3_20261102) · [feduba_targetclass_pair_recovery_20261102](feduba_targetclass_pair_recovery_20261102) · [feduba_fixed_cohort_review_20261103](feduba_fixed_cohort_review_20261103) · [feduba_fixed10_foundation_20261103](feduba_fixed10_foundation_20261103) · [feduba_fixed10_clean_delivery_20261103](feduba_fixed10_clean_delivery_20261103) · [feduba_fixed10_sss_20261103](feduba_fixed10_sss_20261103) · [feduba_fixed10_pair_20261103](feduba_fixed10_pair_20261103) · [feduba_author_archive_review_20261103](feduba_author_archive_review_20261103) · [feduba_fixed10_sss_direction_diagnosis_20261103](feduba_fixed10_sss_direction_diagnosis_20261103) · [feduba_related_helper_positive_20261103](feduba_related_helper_positive_20261103) · [feduba_related_helper_positive_evaluation_20261103](feduba_related_helper_positive_evaluation_20261103) · [feduba_positive_evaluation_prefix_archive_20261103](feduba_positive_evaluation_prefix_archive_20261103) · [feduba_rng_policy_source_review_20261103](feduba_rng_policy_source_review_20261103) · [feduba_positive_independent_recovery_20261103](feduba_positive_independent_recovery_20261103) · [feduba_concoct_helper_source_review_20261103](feduba_concoct_helper_source_review_20261103)

<a id="d01"></a>

## D01 · HRAC·GLR·정상 설명 집합

**가설 한 줄: 과거 상쇄 기여를 누적하면 같은 정상 보정 예산의 단순 기준선보다 위험한 삭제를 잘 찾는다.**

**판정: 기존 점수 보류**

[실험 시작 이유와 실제 실행 과정 읽기](../experiments/02-detection/D01-training-history/README.md)

- **조건:** 보존 글로벌·참여자 이력; 요청 시점까지의 관측만 사용해야 함.
- **정상 대조·비교:** 정상 실행 간 비교와 동일 정상 보정 자료의 단순 기준선.
- **결과:** 정상 실행 간12/40 경보는 보정으로 감소했지만 기준선 대비 우월성이 남지 않았다. GLR 최대값은 한 라운드 잔차로 설명됐고 정상 설명 집합11요청은 모두 미판정이었다.
- **non-IID에 대해 남길 교훈:** 정상 기여 규모·분포도 큰 잔차를 만든다. 이력이 있다는 사실만으로 악성 기여를 식별하지 못한다.
- **반복하지 않을 주장:** 이력 전체가 불가능하다고 단정하거나 같은 잔차를 누적한 점수를 새 판별 원리로 소개하지 않는다.
- **재검토 조건:** 동일 정보·정상 보정 예산의 기준선보다 추가로 구별하는 증거가 필요하다.

**원문·증거:**

- [research/03_detection/parked/history/README.md](03_detection/parked/history/README.md)
- [research_audit_20261019/detection/history.md](../research_audit_20261019/detection/history.md)
- [research_audit_20261019/detection/normal_set.md](../research_audit_20261019/detection/normal_set.md)

**묶은 폴더:** [history](03_detection/parked/history) · [01_history_prediction](03_detection/01_history_prediction)

<a id="d02"></a>

## D02 · FLForensics식 영향력과 정상 참조 보정

**가설 한 줄: 의심 입력과 정상 참조 입력의 이력 영향을 비교하면 정상 non-IID와 공격의 혼동이 줄어든다.**

**판정: 구별 실패**

[실험 시작 이유와 실제 실행 과정 읽기](../experiments/02-detection/D02-influence/README.md)

- **조건:** 완전 이력7쌍·부분 이력2사례·실제 전후8쌍; 미지 후보와 실제 업데이트의 내적. 역 Hessian 전체 재현 아님.
- **정상 대조·비교:** 정상 주요 클래스 삭제·무작위 삭제·감염 모델의 정상 요청.
- **결과:** BadFU 정상 참조 초과 영향은 공격1.9765, 정상 주요 클래스 삭제2.0677. 군집 크기2 수정 설정은 공격2/2와 정상3/3 모두 경보했다.
- **non-IID에 대해 남길 교훈:** 정상 참조를 빼도 정상 클래스 기여가 공격처럼 높은 영향 점수를 만들었다.
- **반복하지 않을 주장:** 참조 보정 자체를 non-IID 제거 증명으로 부르거나 역할 순위를 역할 식별 성공으로 세지 않는다.
- **재검토 조건:** 실제 의심 입력 확보와 추적을 구분하고 독립 정상 대조에서 같은 경보율의 이득을 확인한다.

**원문·증거:**

- [research/INFLUENCE_RUN_20261022/FINAL_REPORT.md](INFLUENCE_RUN_20261022/FINAL_REPORT.md)
- [research/INFLUENCE_RUN_20261022/FINAL_SUMMARY.json](INFLUENCE_RUN_20261022/FINAL_SUMMARY.json)

**묶은 폴더:** [INFLUENCE_RUN_20261022](INFLUENCE_RUN_20261022)

<a id="d03"></a>

## D03 · 패치·전역·입력 의존 탐침의 반응 차분

**가설 한 줄: 같은 미지 변형의 실제 모델 전후 반응 차분은 정상 non-IID 삭제와 공격을 구별한다.**

**판정: 공통 구별 미확보**

[실험 시작 이유와 실제 실행 과정 읽기](../experiments/02-detection/D03-input-response/README.md)

- **조건:** 보존 전후8쌍·720후보; 자유 마스크·공통 가산·입력 의존 변형 및 내부 모듈 검사.
- **정상 대조·비교:** 정상 주요 클래스3558개 삭제·임의 삭제·감염 모델 정상 요청; 같은 학습 실행을 공유함.
- **결과:** 예약 자료에서도 점수 겹침이 유지됐다. BadFU 위장 삭제의 선택 차분15.07pp, 감염 모델의 정상 삭제16.18pp. FUBA 보존쌍은 이미 활성화된 진단 조건이다.
- **non-IID에 대해 남길 교훈:** 전후 차분과 참조 보정은 정상 삭제의 클래스별 변화를 자동으로 없애지 못한다.
- **반복하지 않을 주장:** 국소/전역/입력 의존 탐침을 합쳤다는 이유만으로 트리거 종류 독립 탐지를 주장하지 않는다.
- **재검토 조건:** 정상 큰 탈퇴에서 같은 반응이 생기는 반례를 넘는 별도 판별 근거가 필요하다.

**원문·증거:**

- [research/UNKNOWN_TRIGGER_RUN_20261021/RESULTS.md](UNKNOWN_TRIGGER_RUN_20261021/RESULTS.md)
- [research/DETECTION_REVIEW_20261021/RESULTS.md](DETECTION_REVIEW_20261021/RESULTS.md)

**묶은 폴더:** [UNKNOWN_TRIGGER_RUN_20261021](UNKNOWN_TRIGGER_RUN_20261021) · [DETECTION_REVIEW_20261021](DETECTION_REVIEW_20261021) · [STAGE1_BADFU_TEST_20261021](STAGE1_BADFU_TEST_20261021) · [stage1_20261020](stage1_20261020)

<a id="d04"></a>

## D04 · 최신 제출 제외 패치와 역할 판정

**가설 한 줄: 최신 제출분을 제외했을 때 패턴 반응의 부호와 크기는 주입·억제 역할을 구별한다.**

**판정: 구별·역할 판정 실패**

[실험 시작 이유와 실제 실행 과정 읽기](../experiments/02-detection/D04-client-removal/README.md)

- **조건:** 48개 제출 제외 모델과 기존 끝점; 실제 FU 전체와 다름. 선택80장·확인80장.
- **정상 대조·비교:** 정상 보정 실행과 보정 외 정상 실행.
- **결과:** 정상 변화 보정은 FUBA 공격을 놓치고 보정 외 정상2개 중1개를 경보했다. FUBA 역할도 정상 참여자를 잘못 지목했다.
- **non-IID에 대해 남길 교훈:** 정상 기여 제거도 같은 방향의 패치 반응을 만든다.
- **반복하지 않을 주장:** 최신 업데이트 제외를 실제 언러닝 전후로 부르거나 순위1위를 고정 임계값 통과와 혼동하지 않는다.
- **재검토 조건:** 1단계 공격/정상 구별과2단계 역할 식별의 조건·성능을 분리한다.

**원문·증거:**

- [research/two_stage_detection_20261021/RESULTS_KO.md](two_stage_detection_20261021/RESULTS_KO.md)
- [research/two_stage_detection_20261021/PATCH_COMPARISON_AUDIT.md](two_stage_detection_20261021/PATCH_COMPARISON_AUDIT.md)

**묶은 폴더:** [two_stage_detection_20261021](two_stage_detection_20261021)

<a id="d05"></a>

## D05 · 잠재 표현 출력 쏠림 — FreeEagle식 검사

**가설 한 줄: 미지 중간 표현의 특정 출력 쏠림은 정상 큰 탈퇴보다 공격 모델에서 크다.**

**판정: 공통 특징 채택 안 함**

[실험 시작 이유와 실제 실행 과정 읽기](../experiments/02-detection/D05-feature-bias/README.md)

- **조건:** 모델22개·전후13쌍; layer2/3 절단, 클래스별 가상 표현 최적화. 원 논문 전체 재현 아님.
- **정상 대조·비교:** 정상 주요 클래스·무작위·전체 참여자 삭제와 이전 정상 조건.
- **결과:** 대표 BadFU 쏠림 M′=12.983, 이전 정상 비교14.570. 가상 표현이 원하는 클래스로 분류됐어도 공격 특이성이 확보되지 않았다.
- **non-IID에 대해 남길 교훈:** 픽셀 대신 잠재 공간을 탐색해도 정상 분포 편향이 같은 통계를 만들 수 있다.
- **반복하지 않을 주장:** 잠재 공간으로 바꾸면 non-IID 구별이 해결된다는 제안을 새로 시작하지 않는다.
- **재검토 조건:** 기존 D05 반례와 다른 관측·판별 원리를 먼저 제시해야 한다.

**원문·증거:**

- [research/server_features_20261022/REPORT_KO.md](server_features_20261022/REPORT_KO.md)
- [research/server_features_20261022/PRIMARY_SUMMARY.json](server_features_20261022/PRIMARY_SUMMARY.json)

**묶은 폴더:** [server_features_20261022](server_features_20261022)

<a id="d06"></a>

## D06 · 정상 과제 망각 반응 — MASA식 검사

**가설 한 줄: 같은 정상 과제를 잊게 하는 개입에 대한 손실 반응은 공격을 큰 정상 삭제와 구별한다.**

**판정: 큰 정상 탈퇴 혼동**

[실험 시작 이유와 실제 실행 과정 읽기](../experiments/02-detection/D06-forgetting/README.md)

- **조건:** 공개500장·진단 복사본 상승 학습5epoch·개별 제출 융합 검사 포함.
- **정상 대조·비교:** 큰 정상 참여자22.8%/19.3% 삭제·클래스 집중 삭제.
- **결과:** 후 모델 누적 CE는 BadFU 공격27.291, 정상 주요 클래스29.378, 정상22.8%탈퇴67.143. 제출 검사에서 관측 악성4건 중0건, 정상48건 중13건 경보.
- **non-IID에 대해 남길 교훈:** 정상 기여 상실이 공격보다 큰 망각 반응을 만들었다.
- **반복하지 않을 주장:** 정상 손실을 올려 반응이 크면 공격이라고 판정하거나 새 진단 시드를 독립 FL 학습으로 세지 않는다.
- **재검토 조건:** 같은 반응량의 재가중보다 정상 탈퇴 반례를 구별할 근거가 필요하다.

**원문·증거:**

- [research/server_features_20261022/REPORT_KO.md](server_features_20261022/REPORT_KO.md)

**묶은 폴더:** [server_features_20261022](server_features_20261022)

<a id="d07"></a>

## D07 · 서버 OOD 진단 과제·유지율 함정

**가설 한 줄: 서버가 심은 진단 과제의 유지율은 정상 편중 학습보다 독성 학습에 선택적으로 반응한다.**

**판정: 파일럿 구별 실패**

[실험 시작 이유와 실제 실행 과정 읽기](../experiments/02-detection/D07-diagnostic-task/README.md)

- **조건:** 난수200장 진단 과제 삽입 후 통제 로컬 학습; 실제 FU 전체 실험 아님.
- **정상 대조·비교:** 정상 균형·정상 편중2048/8192장·독성·위장 혼합.
- **결과:** 정상 편중8192장도 최대 유지율100%, 독성은95/100%. 출력 쏠림 제거와 정상 출력 보존 후속에서도 공통 분리를 확보하지 못했다.
- **non-IID에 대해 남길 교훈:** 함정을 추가해도 최종 점수가 유지율/반응량이면 정상 학습이 같은 값을 만들 수 있다.
- **반복하지 않을 주장:** 서버가 비밀 과제를 심었다는 사실 자체를 공격 특이성으로 취급하지 않는다.
- **재검토 조건:** 정상 기능·함정 학습 유효성·큰 정상 기여 대조를 함께 만족해야 한다.

**원문·증거:**

- [research/server_features_20261022/REPORT_KO.md](server_features_20261022/REPORT_KO.md)
- [research/server_features_20261022/indicator_pilot/PROTOCOL.json](server_features_20261022/indicator_pilot/PROTOCOL.json)
- [research/server_features_20261022/indicator_debiased/PROTOCOL.json](server_features_20261022/indicator_debiased/PROTOCOL.json)

**묶은 폴더:** [indicator_pilot](server_features_20261022/indicator_pilot) · [indicator_debiased](server_features_20261022/indicator_debiased)

<a id="d08"></a>

## D08 · 같은 잔류 참여자·클래스 균등·Conv/FC 개입

**가설 한 줄: 같은 잔류 참여자가 같은 개입에 보이는 실제 언러닝 전후 응답은 공격과 큰 정상 non-IID 탈퇴를 구별한다.**

**판정: 핵심 반례 — 구별 실패**

[실험 시작 이유와 실제 실행 과정 읽기](../experiments/02-detection/D08-matched-clients/README.md)

- **조건:** 전후 동일 잔류 집합·자료·가중치·양음 교란; 새 참여자 응답을 실제 계산. 공개 참조 응답 보정 포함.
- **정상 대조·비교:** 동일5시점 FU 규칙의 BadFU 공격과 정상22.790%/19.336%전체 탈퇴; 보존850삭제 대조 별도.
- **결과:** 주 Conv D: 공격0.75848, 정상19.3%탈퇴0.75525, 정상22.8%탈퇴0.76188. 공격이 정상 두 값 사이에 놓였다. 보존850쌍도 공격0.70794/정상0.70360으로 가까웠다.
- **non-IID에 대해 남길 교훈:** 같은 참여자 고정은 구성 변화를 통제할 뿐이다. 큰 정상 탈퇴도 손실 곡률·복구 반응을 바꾼다. 클래스 균등화는 클래스 내부 분포 차이를 없애지 못한다.
- **반복하지 않을 주장:** 협조 참여자·참조 보정·양음 교란·함정을 추가하면 반응량 비교가 자동으로 해결된다고 제안하지 않는다.
- **재검토 조건:** D08의 정상 두 값 사이 공격 반례를 왜 구별할 수 있는지 새 관측의 구체적 판별 원리부터 설명한다.

**원문·증거:**

- [research/active_fu_pairs_20261022/REPORT_KO.md](active_fu_pairs_20261022/REPORT_KO.md)
- [research/active_fu_pairs_20261022/FINAL_ASSESSMENT.json](active_fu_pairs_20261022/FINAL_ASSESSMENT.json)
- [research/active_unlearning_audit_20261022/REPORT_KO.md](active_unlearning_audit_20261022/REPORT_KO.md)

**묶은 폴더:** [active_fu_pairs_20261022](active_fu_pairs_20261022) · [active_unlearning_audit_20261022](active_unlearning_audit_20261022)

<a id="d09"></a>

## D09 · 동일 성공률의 역산 비용

**가설 한 줄: 같은 목표 오분류 성공률을 맞추면 공격은 정상 삭제보다 특정 클래스의 변형 비용을 더 낮춘다.**

**판정: 제한적 관찰·안정성 미확보**

[실험 시작 이유와 실제 실행 과정 읽기](../experiments/02-detection/D09-inversion-cost/README.md)

- **조건:** 고정 모델·공통 가산/마스크 최적화; 유한 탐색의 성공 비용 상한이며 인증된 최소 거리가 아님.
- **정상 대조·비교:** 정상850삭제·클래스 집중·22.8%/19.3%전체 탈퇴. 전체 FU 절차가 같지 않은 표는 따로 해석.
- **결과:** 초기 가산 조건에서 두 초기화를 합치면 순서가 나뉘었지만 단일 초기화에서는 공격 최저30.20%와 정상 최고46.37%로 역전. 마스크 비용은 정상 무작위 삭제에서도 공격보다 크게 감소했다.
- **non-IID에 대해 남길 교훈:** 정상 클래스 지지 자료의 제거도 경계를 움직여 비용을 낮춘다.
- **반복하지 않을 주장:** 최소 마진·최소 섭동 거리라는 이름으로 단순 감소율을 새 해결책처럼 제안하지 않는다.
- **재검토 조건:** D10의 후속 제한적 관찰과 D11의 반례를 함께 읽고 독립 FL/정상 대조를 구분한다.

**원문·증거:**

- [research/boundary_validation_20261022/REPORT_KO.txt](boundary_validation_20261022/REPORT_KO.txt)
- [research/boundary_validation_20261022/FINAL_RESULTS.json](boundary_validation_20261022/FINAL_RESULTS.json)

**묶은 폴더:** [boundary_validation_20261022](boundary_validation_20261022) · `boundary_mask_validation_20261022` (로컬 보관)

<a id="d10"></a>

## D10 · 비용 보정·자료 증가·기존 체크포인트 재검사

**가설 한 줄: 독립 자료에서 성공률을 확인하고 정상 공통 변화를 보정하면 비용 비교의 편차가 줄어든다.**

**판정: 제한된 BadFU 지지**

[실험 시작 이유와 실제 실행 과정 읽기](../experiments/02-detection/D10-cost-correction/README.md)

- **조건:** 같은 모델에서320장 탐색/320장 보정;1200회 및 초기화 묶음 반복. 실제 FL 시드 반복 아님.
- **정상 대조·비교:** 동일5시점 FU의 큰 정상 삭제와 별도850-vs850 보존쌍; 정확도 유지 여부 별도.
- **결과:** 동일 단축 FU에서 공격 보정58.88%, 큰 정상22.76/14.95%로 나뉘었지만 공격 정확도88.25→79.00%. 기존850-vs850에서는83.66% 대23.93%의 제한적 관찰. 빠른 후속 FUBA는 목표 재현 실패 조건이었다.
- **non-IID에 대해 남길 교훈:** 일부 표본의 분리는 보존하지만 큰 정상 탈퇴·기능 유지·새 학습 시드·FUBA 일반화가 모두 해결된 것은 아니다.
- **반복하지 않을 주장:** 유리한850삭제 결과만 가져와 non-IID 전체 또는 범용 탐지 성공으로 확대하지 않는다.
- **재검토 조건:** 원 대조의 삭제 방식·정확도·학습 실행 단위를 함께 보고한다.

**원문·증거:**

- [research/cost_conditions_20261022/REPORT_KO.txt](cost_conditions_20261022/REPORT_KO.txt)
- [research/existing_checkpoint_cost_20261023/REPORT_KO.txt](existing_checkpoint_cost_20261023/REPORT_KO.txt)
- [research/rapid_checkpoint_validation_20261023/REPORT_KO.txt](rapid_checkpoint_validation_20261023/REPORT_KO.txt)

**묶은 폴더:** [cost_conditions_20261022](cost_conditions_20261022) · [existing_checkpoint_cost_20261023](existing_checkpoint_cost_20261023) · [rapid_checkpoint_validation_20261023](rapid_checkpoint_validation_20261023)

<a id="d11"></a>

## D11 · FUBA 이미지별 최소 비용과 수학적 반례

**가설 한 줄: 이미지별 변형을 허용해도 공격 삭제는 정상 삭제보다 특정 클래스의 변형 비용을 크게 낮춘다.**

**판정: 주력 채택 안 함·입력 한계**

[실험 시작 이유와 실제 실행 과정 읽기](../experiments/02-detection/D11-minimum-cost/README.md)

- **조건:** 전후 모델·정상 라벨 이미지·입력 기울기;95%이미지의 Linf 성공 비용. 실제G 미제공.
- **정상 대조·비교:** 정상 같은 참여자 삭제; 큰 전체 탈퇴 대조와 잠복 재현은 미완료.
- **결과:** 정밀 비용 점수는 공격11.30, 정상27.49. 별도 수학 예에서는 기존 오류 경로0.01, 새 공격 경로0.04라 최소 비용이 전후 모두0.01이다.
- **non-IID에 대해 남길 교훈:** 정상 삭제도 한 클래스 비용을 낮추며, 공격이 새 오류 경로를 만들어도 최소 비용 요약은 이를 버릴 수 있다.
- **반복하지 않을 주장:** 이 결과를 유효한 잠복 FUBA의 전체 불가능성으로 확대하지 않는다. 비용·마진 점수를 단순히 바꿔 반복하지 않는다.
- **재검토 조건:** 유효한 FUBA쌍과 큰 정상 탈퇴를 먼저 확보하고 요약에서 사라지는 정보를 무엇으로 관측할지 밝혀야 한다.

**원문·증거:**

- [research/fuba_observation_20261023/README_KO.txt](fuba_observation_20261023/README_KO.txt)
- [research/fuba_observation_20261023/fine_pilot/REPORT_KO.txt](fuba_observation_20261023/fine_pilot/REPORT_KO.txt)
- [research/fuba_observation_20261023/cost_counterexample.py](fuba_observation_20261023/cost_counterexample.py)

**묶은 폴더:** [fuba_observation_20261023](fuba_observation_20261023)

<a id="d12"></a>

## D12 · 자료 없는 조건부 전환과 이력 결합

**가설 한 줄: 원본 예측을 보존한 전후 목표 전환과 같은 기능의 억제·강화 이력을 결합하면 공격을 찾는다.**

**판정: 독립 입력 재현 실패**

[실험 시작 이유와 실제 실행 과정 읽기](../experiments/02-detection/D12-data-free-probes/README.md)

- **조건:** 합성 pseudo-label 입력;마스크/공통 가산 탐색;보존 제출 이력;11쌍 후13쌍 확장.
- **정상 대조·비교:** 정상 클래스 집중·무작위·큰 전체 탈퇴; 서로 다른 FU 종류 분리.
- **결과:** 모든 최종 경보가0. 대표 BadFU는 실제 트리거를 평가자에게 받으면 합성 확인30/36 전환이 있지만 자동 paired후보의 확인 전환은0이었다.
- **non-IID에 대해 남길 교훈:** 반응 크기에서 기능 사건으로 바꿔도 탐색과 독립 확인이 성공해야 한다. 경보0은 구별 성공이 아니다.
- **반복하지 않을 주장:** 의미가 확인되지 않은 합성 입력 적합을 공격 증거로 쓰거나 실제 트리거 제공 진단을 서버 탐지 성공으로 세지 않는다.
- **재검토 조건:** 이력 추가 이전에 미지 조건의 독립 입력 재현을 검증해야 한다.

**원문·증거:**

- [research/request_conditioned_federaser_20261022/FINAL_REPORT_KO.md](request_conditioned_federaser_20261022/FINAL_REPORT_KO.md)
- [research/request_conditioned_federaser_20261022/SUMMARY.json](request_conditioned_federaser_20261022/SUMMARY.json)

**묶은 폴더:** [request_conditioned_federaser_20261022](request_conditioned_federaser_20261022)

<a id="d13"></a>

## D13 · 고정 조건·자유 마스크·특징 변환 비교

**가설 한 줄: 미지 입력 조건에서의 일관된 전후 목표 전환은 정상 non-IID와 공격성 삭제를 구별한다.**

**판정: 범용 탐지 미확보**

[실험 시작 이유와 실제 실행 과정 읽기](../experiments/02-detection/D13-transform-families/README.md)

- **조건:** 보존13쌍·합성/정상40장 탐색·실제320장 확인;최소5source의80%전환 규칙.
- **정상 대조·비교:** 대조9요청에는 감염 모델의 정상 요청도 포함. 독립 학습13회가 아님.
- **결과:** 정상 이미지+고정48종은 악성 요청2/4와 대조0/9경보. 자유 마스크·특징 공간 변환은 공격0/4. 성공2건은 BadFU 유지 재학습쌍이었다.
- **non-IID에 대해 남길 교훈:** 일부 알려진 형태의 후보 성공을 공격 유형 독립성으로 확대할 수 없다.
- **반복하지 않을 주장:** 입력/특징 공간의 이름만 바꾸어 아직 시도하지 않은 범용 방법처럼 제안하지 않는다.
- **재검토 조건:** D14 규칙 학습의 일반화 실패까지 함께 설명해야 한다.

**원문·증거:**

- [research/cross_attack_search_20261022/SHORT_REPORT_KO.md](cross_attack_search_20261022/SHORT_REPORT_KO.md)
- [research/cross_attack_search_20261022/OBSERVER_COMPLETE.json](cross_attack_search_20261022/OBSERVER_COMPLETE.json)

**묶은 폴더:** [cross_attack_search_20261022](cross_attack_search_20261022)

<a id="d14"></a>

## D14 · 색·가산·왜곡을 함께 학습한 입력 의존 규칙

**가설 한 줄: 공격 모양을 지정하지 않은 변형 규칙을 학습하고 독립 입력에서 확인하면 여러 공격에 공통 탐지를 적용할 수 있다.**

**판정: 일반화·구별 실패**

[실험 시작 이유와 실제 실행 과정 읽기](../experiments/02-detection/D14-conditional-transform/README.md)

- **조건:** 입력 의존 Tθ의480스텝 학습;합성/정상40장·확인400장;모델쌍13개.
- **정상 대조·비교:** 악성4요청·대조9요청, 클래스 집중 삭제 포함.
- **결과:** 두 학습 조건 모두 공격0/4·대조0/9경보. 학습 전환100%였던 BadFU의 확인14.0%, 정상 클래스 집중 삭제의 확인28.2%.
- **non-IID에 대해 남길 교훈:** 변형 표현 범위를 넓히면 정상 모델의 일반 적대적 취약성도 찾아낸다. 학습 적합만으로 공격 특이성이 생기지 않는다.
- **반복하지 않을 주장:** 생성기·특징 공간·왜곡을 추가하면 해결된다고 주장하지 않는다.
- **재검토 조건:** 새 관측과 독립 일반화 근거가 기존 D14와 어떻게 다른지 먼저 확인한다.

**원문·증거:**

- [research/rule_transform_20261022/SHORT_RESULTS_KO.md](rule_transform_20261022/SHORT_RESULTS_KO.md)
- [research/rule_transform_20261022/RESULTS_KO.md](rule_transform_20261022/RESULTS_KO.md)

**묶은 폴더:** [rule_transform_20261022](rule_transform_20261022)

<a id="d15"></a>

## D15 · 전후 공동 탐색200회와 정상 협조자 확인

**가설 한 줄: 전후를 함께 탐색하고 정상 참여자의 독립 확인을 받으면 큰 정상 탈퇴와 공격성 삭제를 더 잘 구별한다.**

**판정: 두 시드 일관 구별 실패**

[실험 시작 이유와 실제 실행 과정 읽기](../experiments/02-detection/D15-joint-search/README.md)

- **조건:** 승인된 실제 BadFU2학습 시드·전후5쌍;3변형군·2탐색 초기값;정상 참여자1/2/3 각512장.
- **정상 대조·비교:** 감염 모델 정상850삭제·정상850삭제·19.336%정상 전체 탈퇴;모든 후보를 선택 후 확인.
- **결과:** paired공개 오류: 첫 공격44.78%, 추가시드 공격7.00%, 큰 정상8.00%. 협조 확인에서도 확실한 공통 분리 미확보.
- **non-IID에 대해 남길 교훈:** 정상 협조자의 자료는 확인 근거를 늘리지만 공격과 정상 탈퇴를 구별하는 특징을 자동으로 만들지 않는다.
- **반복하지 않을 주장:** clean 자료·협조 참여자만 추가하면 해결된다는 제안을 반복하지 않는다. 후기 층 변화량 추천은 D16에 따라 철회.
- **재검토 조건:** D17의 후속 결과와 조건 차이를 같이 읽어 유리한 시드만 선택하지 않는다.

**원문·증거:**

- [research/paired_probe_validation_20261023/REPORT_KO.txt](paired_probe_validation_20261023/REPORT_KO.txt)
- [research/paired_probe_validation_20261023/FINAL_EVIDENCE.json](paired_probe_validation_20261023/FINAL_EVIDENCE.json)
- [research/differential_audit_proposal_20261023/PROPOSAL_KO.txt](differential_audit_proposal_20261023/PROPOSAL_KO.txt)

**묶은 폴더:** [paired_probe_validation_20261023](paired_probe_validation_20261023) · [differential_audit_proposal_20261023](differential_audit_proposal_20261023)

<a id="d16"></a>

## D16 · 후기 Conv·FC 변화량 추천 철회

**가설 한 줄: 후기 층 반응 변화량은 기능 검사에서 놓친 공격을 추가로 구별한다.**

**판정: 사용자 지시로 주력 제외**

[실험 시작 이유와 실제 실행 과정 읽기](../experiments/02-detection/D16-retired-magnitude/README.md)

- **조건:** paired-probe의20Conv+FC 관측과 후속 H3 분석;같은 모델과 선택 탐침을 공유.
- **정상 대조·비교:** 소수 승인 전후쌍·큰 정상 탈퇴 한 건;독립 운영 오탐 보정 없음.
- **결과:** 유리했던 수치 기록은 보존하지만 주력 추천을 철회했다. 반응 크기만으로 공격 특이성을 입증하지 못했다.
- **non-IID에 대해 남길 교훈:** 정상 non-IID도 내부 반응을 크게 바꾼다. 일부 층의 숫자가 벌어졌다는 사실만으로 D08의 반례가 해소되지 않는다.
- **반복하지 않을 주장:** norm·cosine·CKA·RMS·민감도·drift 등으로 이름을 바꾸어 같은 주장을 되살리지 않는다.
- **재검토 조건:** 단순 변화량을 새 공격 탐지 제안으로 사용하지 않는 사용자 제약을 따른다.

**원문·증거:**

- [research/paired_probe_validation_20261023/DIRECTION_STATUS_20261023.txt](paired_probe_validation_20261023/DIRECTION_STATUS_20261023.txt)
- [research/paired_probe_validation_20261023/REPORT_KO.txt](paired_probe_validation_20261023/REPORT_KO.txt)

**묶은 폴더:** [paired_probe_validation_20261023](paired_probe_validation_20261023)

<a id="d17"></a>

## D17 · 직접400/800과 노출 복사본400

**가설 한 줄: 진단용 복사본에서 정상 기능을 약화한 뒤 탐색하면 원래 모델에서 공격 행동을 더 잘 발견한다.**

**판정: 노출 가설 기각·직접 탐색 한정 관찰**

[실험 시작 이유와 실제 실행 과정 읽기](../experiments/02-detection/D17-direct-search/README.md)

- **조건:** 승인 BadFU2학습 시드·5쌍·신규 분할·3변형군;최종 확인은 원본 모델.15개 결과 독립 native재계산 일치.
- **정상 대조·비교:** 감염 정상850·깨끗한850·19.336%전체 탈퇴. 큰 정상 탈퇴 한 건, 동일 데이터 분할.
- **결과:** 직접400: 공격56.22/56.00%, 정상14.78/5.22/7.33%. 노출400: 공격2.67/69.22%, 정상10.33/2.67/2.00%. 노출 개선은 시드 간 불안정. 직접 탐색의 강한 후보는 마스크였다.
- **non-IID에 대해 남길 교훈:** 이번 소수 조건에서 기능 오류 비율이 나뉜 관찰은 남긴다. 트리거 종류에 독립적이거나 정상 non-IID 전반을 해결한 탐지기는 아니다.
- **반복하지 않을 주장:** D15 대비 개선을 탐색 횟수 하나의 인과 효과로 단정하거나 현재 결과를 범용 탐지 입증으로 보고하지 않는다.
- **재검토 조건:** 이전200회와 자료·초기값·동률 처리도 다르다는 조건을 보존한다. 새 주력 선정 전 요구사항 전체를 다시 대조한다.

**원문·증거:**

- [research/exposure_validation_20261023/RESULTS_KO.txt](exposure_validation_20261023/RESULTS_KO.txt)
- [research/exposure_validation_20261023/FINAL_EVIDENCE.json](exposure_validation_20261023/FINAL_EVIDENCE.json)
- [research/exposure_validation_20261023/INDEPENDENT_REPLAY.json](exposure_validation_20261023/INDEPENDENT_REPLAY.json)
- [research/detection_decision_20261023/FOLLOWUP_COMPLETED_20261023.txt](detection_decision_20261023/FOLLOWUP_COMPLETED_20261023.txt)

**묶은 폴더:** [exposure_validation_20261023](exposure_validation_20261023) · [detection_decision_20261023](detection_decision_20261023)

<a id="t01"></a>

## T01 · 독성 유무의 원인 대조와 요약 점수 반례

**가설 한 줄: 같은 위장 삭제라도 독성 기여가 남을 때 특정 조건의 오분류가 더 크게 증가한다.**

**판정: 평가자 진단·조건부 증거**

[실험 시작 이유와 실제 실행 과정 읽기](../experiments/03-mechanism/T01-causal-controls/README.md)

- **조건:** 기존 조정 실험의 실제 트리거·독성/위장 구성·역할을 사용하는 원인 분석;서버 입력 아님.
- **정상 대조·비교:** B+P+C→B+P 대 B+C→B, 라벨 복원 대조. 환경 차이와 사후 부분집합 제한 보존.
- **결과:** 정상 원본을 모두 맞힌880장에서도 독성 유지의 증가68.41pp, 독성 없음0.34pp였다. 최소 비용이 새 오류를 버리는 반례도 별도 보존했다.
- **non-IID에 대해 남길 교훈:** 실제 행동 차이가 존재함과 서버가 그 차이를 찾아 정상 삭제와 구별함은 다르다.
- **반복하지 않을 주장:** 평가자가 아는 독성 제거 기준 모델·실제 트리거를 서버가 쉽게 얻는 것으로 가정하지 않는다.
- **재검토 조건:** 추가 관측을 요구하면 획득 방식·비용·신뢰와 정보 누출을 명시한다.

**원문·증거:**

- [research/mechanism_first_20261022/REPORT_KO.md](mechanism_first_20261022/REPORT_KO.md)
- [research/fuba_observation_20261023/README_KO.txt](fuba_observation_20261023/README_KO.txt)

**묶은 폴더:** [mechanism_first_20261022](mechanism_first_20261022) · [04_theory](04_theory) · [limited_information_literature_20261022](limited_information_literature_20261022)

<a id="p01"></a>

## P01 · 삭제 전후 반응 전이 정화

**가설 한 줄: 정상 변경을 작게 허용할 때 삭제 전 반응 전이는 삭제 후 자기증류보다 공격을 더 낮춘다.**

**판정: 제한된 정화 관찰**

[실험 시작 이유와 실제 실행 과정 읽기](../experiments/04-purification/P01-response-transfer/README.md)

- **조건:** 조정 BadFU형4FL시드;동일 검증KL상한, 실제 사용KL 완전 일치 아님.
- **정상 대조·비교:** 삭제 후 자기증류, KL상한0.010/0.020.
- **결과:** KL0.010에서 평균ASR 자기증류29.19%/전이17.36%, KL0.020에서15.03%/16.74%로 순서 역전.
- **non-IID에 대해 남길 교훈:** 정화 효과는1단계 공격/정상 구별의 성공 증거가 아니다.
- **반복하지 않을 주장:** 탐지·역할 식별·정화 결과를 한 성공으로 합치거나 망각 품질을 공격 억제로 대신하지 않는다.
- **재검토 조건:** 별도 정상 변경·삭제 품질 제약과 비교 조건을 유지한다.

**원문·증거:**

- [research/02_purification/derived/response_transfer/README.md](02_purification/derived/response_transfer/README.md)
- [research_20261018/response_transport/RESULT_REPORT.txt](../research_20261018/response_transport/RESULT_REPORT.txt)

**묶은 폴더:** [response_transfer](02_purification/derived/response_transfer) · [response_transport](../research_20261018/response_transport)

<a id="p02"></a>

## P02 · 마지막 분류층 교정

**가설 한 줄: 특징 추출기를 유지한 분류층 교정으로 정상 성능을 유지하며 공격을 낮출 수 있다.**

**판정: 제한된 정화 관찰**

[실험 시작 이유와 실제 실행 과정 읽기](../experiments/04-purification/P02-classifier-repair/README.md)

- **조건:** 저자 코드 계열 한 실제FU후 모델;삭제 전 ASR이 이미 높았음. 패치 시드 반복은 FL 반복 아님.
- **정상 대조·비교:** 패치 수·반례 보강·후보 선택 규칙·유지 재학습 모델 비교.
- **결과:** 한 모델에서ASR99.51→11.58–12.62%, 정확도86.96→86.94–87.04%. 유지 재학습 모델에서 반례 보강은 악화됐고 선택 점수 개선은 사후 분석이었다.
- **non-IID에 대해 남길 교훈:** 정화 후보가 존재하는 것과 정상/공격을 먼저 식별하는 것은 별개다.
- **반복하지 않을 주장:** 성공 후보의 사후 선택을 서버의 고정 선택 규칙 성능으로 보고하지 않는다.
- **재검토 조건:** 후보 생성과 선택을 나눠 새 모델에서 확인해야 한다.

**원문·증거:**

- [research/02_purification/derived/classifier_repair/README.md](02_purification/derived/classifier_repair/README.md)
- [research_audit_20261019/purification/head.md](../research_audit_20261019/purification/head.md)

**묶은 폴더:** [classifier_repair](02_purification/derived/classifier_repair)

<a id="p03"></a>

## P03 · A/C 손실 분산·프루닝·헤드 증류 파일럿

**가설 한 줄: 잔류 참여자의 정상 자료에서 손실 변화의 집단 간 분산은 정상 삭제보다 위장 삭제 때 크다.**

**판정: 목표 판정 제외 — 입력 선택 오류**

[실험 시작 이유와 실제 실행 과정 읽기](../experiments/04-purification/P03-purification-pilot/README.md)

- **조건:** 잘못 선택한 seed42 full6 고사전ASR 진단 조건;승인된 잠복 전후쌍이 아님. 원 A1/A2/C가 별도 가설인 사실은 원문을 따른다.
- **정상 대조·비교:** 삭제량·출발 모델도 짝맞춤되지 않음.
- **결과:** 실행과 수치는 보존하지만 목표한 잠복 공격의 탐지/정화 가설 판정에서 제외했다.
- **non-IID에 대해 남길 교훈:** 큰 정상 기여는 잔류 손실 분산도 만들 수 있다. 부적합 입력에서 유리한 값을 얻어도 이를 해소하지 못한다.
- **반복하지 않을 주장:** 파일명·최신 날짜·높은 ASR로 모델을 고르지 않는다. 실패/부분 기록을 지우지 않는다.
- **재검토 조건:** 모델 선택은 R01을 먼저 따르고 이 기록을 유효 잠복 검증의 대체물로 쓰지 않는다.

**원문·증거:**

- [research/ac_feasibility_20261023/README.md](ac_feasibility_20261023/README.md)
- [research/ac_feasibility_20261023/SOURCE_AUDIT.json](ac_feasibility_20261023/SOURCE_AUDIT.json)

**묶은 폴더:** [ac_feasibility_20261023](ac_feasibility_20261023)

<a id="n01"></a>

## N01 · 신뢰 기준 모델을 추가하면 해결된다는 직전 제안

**가설 한 줄: 같은 삭제 조건을 반영한 신뢰 기준 모델을 추가하면 공격의 기능 훼손과 정상 non-IID 손실을 구별할 수 있다.**

**판정: 미검증·자동 실행 대상 아님**

[실험 시작 이유와 실제 실행 과정 읽기](../experiments/05-parked/N01-trusted-reference/README.md)

- **조건:** 2026-10-23 대화상의 제안. 실제 획득 가능한 참조·분포 대표성·공격 특이성 검증 없음.
- **정상 대조·비교:** 동일 정상 탈퇴를 반영한 유효 기준 모델과 큰 정상 대조가 필요하지만 아직 만들어 검증하지 않음.
- **결과:** 사용자가 다시 지적한 핵심은 단순 반응량으로는 큰 정상 non-IID 탈퇴를 구별하지 못한다는 점이다. 참조 모델 추가를 그 해결책으로 확정하지 않는다.
- **non-IID에 대해 남길 교훈:** 공개 참조 보정(D02/D08)과 정상 협조자 확인(D15)도 이미 실패 조건을 보였다. 독립 기준 모델은 이들과 다른 조건이지만 추가 정보라는 이유만으로 구별이 보장되지 않는다.
- **반복하지 않을 주장:** 존재하지 않는 깨끗한 기준 모델을 기본 서버 정보로 가정하거나 또 다른 반응 차분을 근본 해결책으로 소개하지 않는다.
- **재검토 조건:** 먼저 D08/D15와의 차이, 실제 획득 방법, 큰 정상 탈퇴에서도 왜 같은 증거가 생기지 않는지 명시해야 한다. 새 실행은 현재 정리 요청에 포함되지 않는다.
- **출처 구분:** 본 대화 2026-10-23의 직전 제안과 최신 사용자 정정. 연결된 파일들은 해당 제안의 실행 결과가 아니라 기존 반례다.

**원문·증거:**

- [research/active_fu_pairs_20261022/REPORT_KO.md](active_fu_pairs_20261022/REPORT_KO.md)
- [research/paired_probe_validation_20261023/REPORT_KO.txt](paired_probe_validation_20261023/REPORT_KO.txt)

<a id="d18"></a>

## D18 · 클린 특징 부분공간에 직교하는 FC 변화 재검사

**가설 한 줄: 클린 참조 사진50장의 특징 부분공간에 직교하는 FC 변화의 클래스별 이상도는 BadFU 위장 삭제와 큰 정상 non-IID 삭제를 구별한다.**

**판정: 한 시드 분리 관측·투영 추가 가치 미입증**

[실험 시작 이유와 실제 실행 과정 읽기](../experiments/02-detection/D18-feature-projection/README.md)

- **조건:** 사용자 직접 실행 요청에 따른 유한 진단. 명시적 badfu.confirmed.s20261023.v1/retrain_activation/local 봉인 검증; 유지 자료 전체 재학습 전후3쌍/실제 FL1시드. 균형50장·pre 특징·중심화PCA95%·k40·leave-one-out Z>=6을 계산 전에 고정.346개 참조/기저 조합을 모두 보존.
- **정상 대조·비교:** 같은 정상850장 삭제와 정상9668/50000(19.336%) 참여자 전체 삭제. 점수 고정 후 별도 실제 트리거9000장 평가. 사후 해석 절제로 투영 전 FC 행 norm의 동일 Z를 비교.
- **결과:** 주조건 수직Z는 공격9.531884, 정상850삭제5.404488, 큰정상3.156397로 공격만 경보했다. 각쌍346설정 모두 같은 경보였다(독립 모델346개가 아님). 독립 Gram 고유분해 검산/1038행/모델 해시 guard가 통과했다. 다만 사후 투영 전 행norm Z도10.871271/4.673667/3.424834로 같은 판정이어서 투영의 추가 판별 가치가 미입증이다. 공격 수직 에너지84.3184%와 정상850의83.8637%는 비슷하며 큰정상도 수직norm이 평행보다 컸다. 현재 고정 프로필의 저자 원평가 함수는 공격CA90.38→90.46/ASR14.2889→100을 확인했다. 과거 clean_pre CA90.80 대비 현재90.78의 불일치/초기exit1/후속TF32 단독 설명 실패를 보존하고, 같은 현재 설정의 원함수·캐시 일치만 확인했다.
- **non-IID에 대해 남길 교훈:** 이 한 시드/세쌍의 유리한 분리는 보존하되 D08/D15의 다른 실제 FU/학습 조건 실패를 대체하지 않는다. 표본 PCA의 직교 잔차를 자연계에 없는 악성 방향으로 동일시할 수 없고, 큰 수직 비율이나 이 세쌍의 분리만으로 트리거 종류에 독립적인 non-IID 해결을 주장할 수 없다.
- **반복하지 않을 주장:** D16의 norm 주력 금지를 유지한다. 표본 재표집/기저 설정을 독립 FL 반복으로 세거나 원문 누락 k/Z 산식을 정확 복제했다고 부르지 않는다. 사후 절제를 주 검정으로 바꾸거나 최초 평가 실패/정밀도 차이를 지우지 않는다. 자동 학습/재시작/정상 또는 FU 분기는 없다.
- **재검토 조건:** 주 가설의 현재 고정 규칙은 이 표본에서 통과했지만 범용/기하학적 추가 가치 주장은 미검증이다. 별도 실행을 요청받으면 새 모델/분할/정상 보정과 투영 전 비교가 필요하며 이번 결과만으로 자동 실행하지 않는다.
- **출처 구분:** 2026-10-25 사용자 제시 수치 검증 직접 실행. 원문에 사진ID/k/중심화/Z 분모 코드가 없어 실행 전 가정을 명시한 재구성. 주 소스 동결/원본 보존; 사후 해석 절제와 평가 진단을 별도 표시.

**원문·증거:**

- [research/manifold_projection_check_20261025/PROTOCOL.txt](manifold_projection_check_20261025/PROTOCOL.txt)
- [research/manifold_projection_check_20261025/FREEZE.json](manifold_projection_check_20261025/FREEZE.json)
- [research/manifold_projection_check_20261025/REPORT_KO.txt](manifold_projection_check_20261025/REPORT_KO.txt)
- [research/manifold_projection_check_20261025/SUMMARY.json](manifold_projection_check_20261025/SUMMARY.json)
- [research/manifold_projection_check_20261025/SCORES.json](manifold_projection_check_20261025/SCORES.json)
- [research/manifold_projection_check_20261025/VERIFICATION.json](manifold_projection_check_20261025/VERIFICATION.json)
- [research/manifold_projection_check_20261025/POSTHOC_ABLATION.json](manifold_projection_check_20261025/POSTHOC_ABLATION.json)
- [research/manifold_projection_check_20261025/BEHAVIOR_EVALUATOR_ONLY_CURRENT.json](manifold_projection_check_20261025/BEHAVIOR_EVALUATOR_ONLY_CURRENT.json)
- [research/manifold_projection_check_20261025/EVALUATION_INCIDENT.txt](manifold_projection_check_20261025/EVALUATION_INCIDENT.txt)
- [research/manifold_projection_check_20261025/EVALUATION_DIAGNOSIS_ADDENDUM.txt](manifold_projection_check_20261025/EVALUATION_DIAGNOSIS_ADDENDUM.txt)

**묶은 폴더:** [manifold_projection_check_20261025](manifold_projection_check_20261025)

<a id="d19"></a>

## D19 · FUBA 과거 진단 전후의 동일 FC 부분공간 점수

**가설 한 줄: D18의 클린50장/PCA95%/FC 수직행 norm Z>=6 고정 규칙은 기존 FUBA 억제 참여자 삭제와 정상 같은 참여자 삭제의 진단 점수를 구별한다.**

**판정: 진단 쌍 분리 미관측·유효 잠복 FUBA는 미검증**

[실험 시작 이유와 실제 실행 과정 읽기](../experiments/02-detection/D19-fuba-projection/README.md)

- **조건:** 명시적 fuba.legacy.s20261020.retained_pairs.diagnostic/diagnostic/local로 기존4개 export를 등록·선택. 같은 D18 수식/사진seed/임계값, native pixel01/linear512,346설정×2쌍=692행. 잠복 재현 실패한 과거 유지자료 재학습 전후로 최신v5와 다르다.
- **정상 대조·비교:** 과거 정상 같은 참여자 삭제 m09→m10. 온전한 큰 정상 탈퇴와 승인 잠복 FUBA 쌍은 없음. 투영전 FC행 norm의 같은Z를 사전 보조비교로 기록.
- **결과:** 주조건 억제 참여자 삭제Z3.417671/정상삭제3.599358, 자동선택은둘다class1, 둘다Z6미만. 각쌍346조건 모두경보0. 투영전Z3.233576/3.562397로도겹침. 독립 Gram 검산/692행/사용전후해시/엄격로드/로드후상태동일 통과. 최초 raw-export BN카운터형식 assertion 실패를 보존하고, verified_v2에서 로드직후기준 비교만 수정했다. 새 학습 없음.
- **non-IID에 대해 남길 교훈:** 이 과거 재현 실패 조건에서 점수 미분리는 보존하지만 유효 잠복 FUBA 탐지 실패나 보편 불가능성으로 해석하지 않는다. D18의 BadFU 클래스별 변화 집중은 투영전에 이미 존재하여 일반 악성 방향을 포착했다는 근거가 아니다. 큰 정상 FUBA 대조는 여전히 미확보다.
- **반복하지 않을 주장:** 재현 실패 FUBA를 탐지양성으로 승격하거나 최신v5단일모델/서로다른라운드를전후쌍으로 섞지 않는다. D16 norm 주력금지는 유지. 단일원인/공격군본질을확정하거나 임계값을사후변경하지 않는다.
- **재검토 조건:** 유효한 억제→활성화 전후와 정상 큰삭제/독립 시드가 확보된 별도 승인 범위에서 검증해야 하며 이번 기록은 자동학습/재시작/분기를 허가하지 않는다.
- **출처 구분:** 2026-10-25 사용자 FUBA 적용 요청에 따른 유한 저장모델 진단. R02의 잠복 재현 실패 정정과 D18의 투영 추가가치 미입증을 유지.

**원문·증거:**

- [research/fuba_projection_check_20261025/PROTOCOL.txt](fuba_projection_check_20261025/PROTOCOL.txt)
- [research/fuba_projection_check_20261025/REPORT_KO.txt](fuba_projection_check_20261025/REPORT_KO.txt)
- [research/fuba_projection_check_20261025/SUMMARY.json](fuba_projection_check_20261025/SUMMARY.json)
- [research/fuba_projection_check_20261025/CASE_REGISTRATION.json](fuba_projection_check_20261025/CASE_REGISTRATION.json)
- [research/fuba_projection_check_20261025/LOAD_FORMAT_DIAGNOSIS.json](fuba_projection_check_20261025/LOAD_FORMAT_DIAGNOSIS.json)
- [research/fuba_projection_check_20261025/LOAD_CHECK_AMENDMENT.txt](fuba_projection_check_20261025/LOAD_CHECK_AMENDMENT.txt)
- [research/fuba_projection_check_20261025/verified_v2/FREEZE.json](fuba_projection_check_20261025/verified_v2/FREEZE.json)
- [research/fuba_projection_check_20261025/verified_v2/SCORES.json](fuba_projection_check_20261025/verified_v2/SCORES.json)
- [research/fuba_projection_check_20261025/verified_v2/VERIFICATION.json](fuba_projection_check_20261025/verified_v2/VERIFICATION.json)
- [research/fuba_projection_check_20261025/verified_v2/CLEAN_EVALUATION.json](fuba_projection_check_20261025/verified_v2/CLEAN_EVALUATION.json)

**묶은 폴더:** [fuba_projection_check_20261025](fuba_projection_check_20261025)

<a id="n02"></a>

## N02 · 공개 코드 정체와 넓은 탐지 주장부터의 반증 감사

**가설 한 줄: 클린 정확도 보존과 삭제 후 조건부 오분류만으로 공격의 필연적 PCA직교성과 정상큰삭제의 정확직교소거를 도출할 수 있다.**

**판정: 필요기하반례 확인·공통 탐지 보류**

[실험 시작 이유와 실제 실행 과정 읽기](../experiments/05-parked/N02-broad-claim-audit/README.md)

- **조건:** 서로다른 upstream source/commit과 선언된 실제 실행을 구분. 두 유한 유리수 함수/자료 반례를 계산 전 동결. 실모델 학습이나 새 탐지점수 튜닝 없음.
- **정상 대조·비교:** 클린4점에서25%정당삭제와, 동일클린span 내부의 정확도보존 전후함수. D08/D15의 실제큰정상삭제 실패와 D18 투영전 비교를 보존.
- **결과:** PR의계획/코드게시후 Fraction 두사례를계산하고독립재실행이일치했다. 정상25%삭제직교기울기0→-1/120, 클린span내정확도보존조건부전환/FC가중치변화0 반례로 제시한보편기하필요조건을기각했다. 공개9파일blob/AST검토는missing models/utils와순위인덱스문제를기록했다. 실제공통탐지성능/모든탐지불가능성은주장하지않는다. 같은고정코드의DISLAB CPU독립검산4명령도통과했고로컬과결과JSON이동일했다. 실제학습반복수는늘지않았다.
- **non-IID에 대해 남길 교훈:** 정상희귀기여의 삭제가 작은분산방향의 결정론적 기울기를 바꿀 수 있는지를 먼저 반증한다. 반례는 D08해결이나 모든탐지불가능성의 증거가 아니다.
- **반복하지 않을 주장:** FUBA/FedUBA/서로다른라운드를 섞거나 단순norm을 새탐지법으로 제안하지 않는다. 좁은한시드 분리를 범용성/낮은운영오탐으로 승격하지 않는다.
- **재검토 조건:** 유효한 코드별실제잠복쌍·동등FU큰정상대조·획득가능한새행동관측·D08/D15구별근거·독립정상보정/중단규칙을 먼저 확보해야 실모델 공통탐지를 재검토한다.

**원문·증거:**

- [research/detection_claim_audit_20261031/PROTOCOL.txt](detection_claim_audit_20261031/PROTOCOL.txt)
- [research/detection_claim_audit_20261031/PLAN.json](detection_claim_audit_20261031/PLAN.json)
- [research/detection_claim_audit_20261031/CODE_REVIEW.txt](detection_claim_audit_20261031/CODE_REVIEW.txt)
- [research/detection_claim_audit_20261031/CLAIMS_AND_GATES.txt](detection_claim_audit_20261031/CLAIMS_AND_GATES.txt)
- [research/detection_claim_audit_20261031/SOURCE_MANIFEST.json](detection_claim_audit_20261031/SOURCE_MANIFEST.json)
- [research/detection_claim_audit_20261031/EVIDENCE.json](detection_claim_audit_20261031/EVIDENCE.json)
- [research/detection_claim_audit_20261031/REPORT_KO.txt](detection_claim_audit_20261031/REPORT_KO.txt)
- [research/detection_claim_audit_20261031/MATH_RESULTS.json](detection_claim_audit_20261031/MATH_RESULTS.json)
- [research/detection_claim_audit_20261031/SOURCE_AUDIT.json](detection_claim_audit_20261031/SOURCE_AUDIT.json)
- [research/detection_claim_audit_20261031/DISLAB_AMENDMENT.txt](detection_claim_audit_20261031/DISLAB_AMENDMENT.txt)
- [research/detection_claim_audit_20261031/DISLAB_VERIFICATION.json](detection_claim_audit_20261031/DISLAB_VERIFICATION.json)

**묶은 폴더:** [detection_claim_audit_20261031](detection_claim_audit_20261031)

