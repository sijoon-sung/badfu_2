# 실험 카드 — 가설·정상 대조·실패 이유

[먼저 연구 인덱스 읽기](INDEX.md) · [전체 폴더](EXPERIMENT_FOLDERS.md)

기존 대표 보고서와 정정을 재검토한 카드에 2026-10-25 사용자 요청의 별도 고정 모델 진단(D18)을 추가 연결. 카드별 원문과 실행/수학/사후진단 범위를 구분한다. 인덱스 생성 자체는 모델 재계산을 수행하지 않는다. 2026-10-31 P04의실제정상집단훼손/고정수정실패/진행중모듈개입을추가하며전체방어성공은미확정으로둔다.

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

**판정: 고정seed 첫새100R/KD10 전달완료·성능미달 / 다음seed GPU자원 대기**

[실험 시작 이유와 실제 실행 과정 읽기](../experiments/01-reproduction/R02-fuba-reproduction/README.md)

- **조건:** stcebra/FUBA 수정 후보와 과거 보존 모델; ity207/FedUBA와 다른 연구.
- **정상 대조·비교:** 같은 생성기를 정상 모델에도 적용한 교차 진단; 정상 삭제 대조의 완료 여부 별도 확인.
- **결과:** 승인된 잠복 활성화 전후쌍은 없다. 기존 정상 모델로의 높은 생성기 전이 기록을 보존한다. v2 시드20261023은100R 저장·연결·집계 오차0·186개 작업자 생성기 그룹 검증 및 로컬 복사를 완료했으나, 전체10000장 정확도71.87%/타깃 제외9000장 ASR99.0889%로 사전 억제10% 기준을 실패했다. 진단 전용 삭제 전 모델이며 후속 대조·삭제는 실행하지 않았다. 저장·회귀검사 통과를 공격 재현 성공으로 세지 않는다. 2026-10-24 원문·실행 감사에서 재가중 방향·억제2단계 입력·단계 순서·가상 집계/γ 실패 처리·학습 조건 불일치를 확인했고 별도 수정 후보의 CPU 회귀15개가 통과했다. 고정 저장 모델 추론에서 로컬 억제와 전체 집계 실패를 구분했다. IBA 결합/프로필 질문과 실자료 재현은 미검증이며 새 학습은 시작하지 않았다. 2026-10-24 사용자 재실행 지시에 따라 공식 소스를 재확보·대조하고 별도 v3 프로필의 DISLAB100R을 시작했다. 추가CPU9개와 실제GPU/MPI20제출·집계오차0·CPU출력 검사를 통과했다. 검사 fixture의 ASR은 억제 증거가 아니며 본 학습 결과는 미완료다. IBA 결합/BN 정책은 명시한 구현 선택으로 고정했고 과거 실패는 보존한다. 2026-10-24 v3는15R 저장 후16R 참여자1의 γ0 로컬 ASR12.9464%(29/224) 실패로 등록 규칙에 따라 중단했다. 15R 전체10000/9000장 독립 재평가는 CA76.10%/ASR8.1333%로 기록과 일치했다. 전체15R 해시·연결·집계 오차0·120개 역할·13개 G그룹을 검증하고, 마지막15R·실패16R·소스·평가 사본을 로컬에 봉인 전달했다.100R 미완료·CA80% 미달이며 잠복 전후쌍/재현 성공이 아니다. 자동 재시작·정상/삭제 분기는 실행하지 않았다. 2026-10-24 사용자 재지시에 따라 별도 v4 제어흐름 프로필로 DISLAB16–100R 연속 실행을 시작했다. 본문Algorithm1 lines9–12의 γ0 반환과 달리v3에 추가했던 whole-MPI 종료를 고쳤고, γ0의 BN 변경도 막았다. 로컬 실패12.9464%는 같은 저장G/모델로 독립 재현하고 미달 상태 그대로 기록했다. 원래 완료된16R client1 학습 단계는 원본 기록과 함께 재사용하고 나머지 실제 학습을 수행한다. 수치·시드·최종100R/CA80/ASR10 기준은 유지하며 중간ASR 경보를 성공으로 표시하지 않는다. 원본 실패/사본은 보존한다. 본 실행 결과는 아직 미완료다. 새16R은15→16 연결·집계 오차0·γ0 실제 제출·같은G·CPU출력 검증을 통과했고 전체시험 평가 기록은CA76.86%/ASR9.3778%다. 최종100R 결과 또는 독립 재평가는 아니다. v4의17–19R 전체시험ASR12.0444/11.5444/12.8333%로 최초 연속 경보가 발생했다. 19R 모델/로그를 별도 보존하고3R의 파일·연결·정확집계0·24역할·4개G그룹 및 고정320/288장 CPU 추론을 검증했다. 17R은 로컬 예상9.5455% 통과 후 실제 전체집계12.0444%였고,3R 모두 억제 참여자가 미선택됐다. 19R 두γ0 제출의 항등성도 통과했다. 예상/실제 집계 간 실패 경로이며 개별 원인의 인과 분리는 미완료다. 원본 v4 학습/최종 기준은 유지하고 새로운 학습·자동 재시작은 하지 않았다. 최종100R은 미완료다. v4는23R 저장 후24R client3의선언gamma상한10에서중단했다. 전체23R/184역할/28G그룹/정확집계0이통과했고 독립10000/9000평가CA77.12%/ASR13.9444%를재현했다. 원본cap분기가중간모델/점수를저장하지못한결함을확인하고별도저장보강CPU검사를통과했다. 사용자승인단일참여자진단은원본G그대로/4단계50epoch였으나gamma2.0통과/2.1실패로원본cap10을재현하지못했다. 마지막23R·원본실패·단계모델·진단을별도봉인하여로컬전달했다.100R은미완료이며원본FL재개/상한확대/다른참여자실행은하지않았다. 2026-10-24 최신100R완료재지시에따라별도v5를사전등록했다.23R동일해시복원후24–100R을계산하며cap10은유지하고최대값미확정의마지막검사통과값을제출해전체FL을계속한다.원본실패/진단은보존하고진단모델을재사용하지않는다.모든학습조건과최종100R/CA80/ASR10은유지하며실행결과는미완료다. v5실제MPI/GPU학습시작과23R복원/집계0/엄격CPU검사를확인했고자동확인fuba-v5-100이최종100R검증·로컬전달까지이어간다.진행중이며최종성공은미확정이다. v5첫24R저장과23→24연결/8역할/집계오차0/같은G/단계RNG6개/소스해시가통과했고25R학습을이어간다.24R기록CA75.48/ASR13.3444는중간미달로보존하며최종100R독립평가성공으로세지않는다. v5의31R효용은gamma10제출후CA10.19/ASR0으로급락했다.원본연결/8역할/집계오차0/실제상한제출동일성이통과했고모델·점수·소스를별도보존했다.ASR0을억제성공으로보지않으며개별인과기여분리는미완료다.원조건을바꾸지않고100R계속실행중이다. 2026-10-25 v5최종100R완료와전체파일/연결/800역할/186G그룹/집계오차0/948단계RNG를검증했다. 독립10000/9000평가CA78.58%/pre-ASR28.6889%가기록과정확히일치해CA80/ASR10게이트는실패했다.32–100R공격자111회는모두로컬gamma0미달/zero제출이었다.완료모델·소스·평가·cap/RNG/31R효용실패·감독복구근거를양쪽봉인전달하고해시/CPU로드/출력을확인했다.단일삭제전진단모델이며잠복전후쌍은없고추가학습/정상/FU를자동시작하지않았다. 2026-10-25 사용자 삭제후 직접 실행 재지시:100R 전달만으로 전체목표를종료한범위를정정하고,원본v5를보존한별도KD-based FU10회로참여자4의실제이력기여제거/무라벨KD/전후pt·로그·고정G평가를사전등록했다.공개코드배열위치/20대신실제ID/weights를연결하고supplementary의10회/clean무라벨KD를따르는정정을명시했다.사전ASR실패를이유로FU실행을생략하지않으며성능성공은미확정이다. 2026-10-25 KD-based FU 실제10회/400batch를완료하고삭제후.pt·전체로그·전후쌍을양쪽보존했다.전CA78.58/ASR28.68888888888889,후CA78.95/ASR28.42222222222222이며동일G전체독립평가가일치했다.실제전후쌍은존재하지만사전억제실패로잠복재현성공은아니다.원문/공개코드정정을기록했고원본v5봉인본은불변이다. 2026-10-25 최신 DISLAB 정상코드 직접 재지시:공개commit/10파일과실제함수를DISLAB에서재검사했다.기존v5가이미고친공개코드결함과새수식SGD/Adam차이를구분하며m4정정은확정하지않았다.저장100R의추가BN보정은로컬gamma0미달을바꾸지않았다.별도v6프로필에서명시된2개업데이트만literalSGD/다른단계Adam및학습BN정책을사전선언하고fresh100R→실제KD10→전후pt/전체로그/독립검증을일회성으로시작했다.로컬·DISLABCPU계약9개와실제학습PID/GPU진행을확인했고실행코드26파일/동일해시/최초CPU출력을로컬전달했다.최종100R/KD10/성능재현은아직미완료이며저자공인유일해석으로부르지않는다.모든원본실패는보존한다. v6첫1R실저장검사:초기모델연결/실제8역할·각50epoch2000배치/400epoch로그/정확집계0의CPU검사가통과했고이후라운드를계속한다.최종100R·KD10성능재현은아직미완료다. v6첫6R방어자계약검사:실제6R의유일한악성역할client4에서4단계각50epoch/1800batch,optimizer Adam·Adam·SGD·SGD,실제G5epoch와동일G보존,unscaled기준최종제출식및집계오차0을CPU검사했다.6R에는Adv-attacker가선택되지않아gamma계약을검사했다고하지않는다.7R학습은계속하며최종재현은미완료다. v6첫7R공격자계약검사:client0의4단계각50epoch/1800batch,Adam·Adam·SGD·Adam,동일G/실제제출/집계0이CPU검사통과했다.최초gamma0로컬ASR10.909090909090908미달로정확한zero제출을확인했으며양수gamma선택통과나점수독립재계산이라고하지않는다.실제7R전체CA70.69/ASR4.222222222222222는중간기록이며최종성공이아니다.8R이후원조건학습을계속한다. 2026-10-26 즉시개입 감사:63R의504역할/전체epoch로그/고정소스23해시를대조했고,실제제출·집계/G·optimizer/RNG 텐서검사를확대했다.28R까지통과후감사stdout OSError22는학습오류와분리보존하고영속로그의별도CPU관측작업으로바로복구했다.9R선택gamma2.3은18/220동일하지만탈락2.4에서CPU24/220대GPU23/220의1장불일치를발견하여원본보존·수치진단중이며전체독립점수통과라고하지않는다.52R cap점수두개는같았다.원래trainer가실제100R+KD10/400batch를완료했고전CA77.8/ASR12.811111111111112,후CA78.03/ASR14.544444444444444로최종성능게이트는미달이다.별도CPU검사로client4의실제41기여가중합·차감·KD10/400고유배치/25000예시·최종상태일치를확인했다.전체100R검증·동일GPU독립평가·로컬전후모델전달은계속한다.다른GPU앱점유로유휴guard가막은것을관측했으며다른앱종료/유휴기준우회/학습재시작은하지않았다. v6보강CPU100R감사완료:100R/800역할/186악성G그룹/1235모델산출파일의해시·연결·optimizer/RNG·제출식·집계0과전체epoch로그/23소스검사를통과했다.관측프로세스는정상종료했다.공격자146회에서zero미달91/첫실패경계36/cap19,양수제출55다.모든gamma독립추론이나원래FINAL_VERIFIED/전체GPU독립평가/로컬전후모델전달완료는아니다.1장CPU/GPU점수차이는보존하며최종검증·전달을계속한다. v6실제전후모델로컬중간보존:PENDING_FINAL_MODELS에실제before/after/fixedG와전체epoch/KD로그등13파일의동일해시·CPU엄격로드/출력을확인했다.수집기소스경로오류는보존·정정했고학습/원격모델은불변이다.최종검토패킷·독립평가·전체KD모델전달·카탈로그guard는미완료이며자동확인을유지한다. v6원래전체CPU검증도100R/800역할/186G/744단계/집계0/KD10·400고유배치/2304파일을통과했다.이후GPU812MiB유휴guard로독립평가가CUDA추론전에실패했고원래감독·평가PID종료/중복평가부재를확인했다.원래실패·로그·소스11파일을양쪽동일해시로보존하고GPU자원결정을요청했다.실제GPU유휴후평가·export만복구하며학습재실행이나기준우회는하지않는다.전체독립평가·최종검토패킷·카탈로그는미완료다. 2026-10-31 사용자는 기존 stcebra/FUBA를 우선하고 논문 Algorithm1/2 일치를 최종 기준으로 재확정했다. 이전 원코드 기반 실행·수정 이력이 없었다는 설명을 정정했다. 별도 고정100R/client1·학습된 previousG99/같은 incoming·앵커·RNG/50개 epoch 데이터순서에서 embedding SGD 대 Adam만 실제50epoch씩 비교했다. 총100epoch/3600batch, 전체10000/9000 평가에서 SGD CA72.97/ASR.6777778, Adam CA72.43/ASR1.7444444로20%p 개선 가설 미지지. 기존 v7 최종전후 지표와 다른 로컬 진단이다. 새A는 원래phase3와 비트 불일치이므로 현재runtime A/B로 한정한다. 새4모델 파일/optimizer/RNG/전체로그 CPU검증과 로컬 해시 전달을 완료했고 새100R/FU·탐지 실행은 하지 않았다. Algorithm1/2 함수 대응과 gamma/BN/IBA 통합의 미확정 선택을 구분했으며 Adam을 정식 알고리즘으로 채택하지 않았다. 모든 기존 실패·카탈로그·기본값을 보존했다. 2026-10-31 학습반경만 .05로 맞춘 같은50epoch/1800batch 진단은CA56.06/ASR84.7222222/정상타깃쏠림37.5888889로효용/쏠림게이트를실패했다. 모델/optimizer/RNG/로그를검증·전달했고전체IBA일정을자동실행하지않았다. 별도논문내MNIST/DBA기준선은원공개BN없는Net/고정패치로Algorithm1/2 fresh100R후실제KD10을사전등록했다. DISLABCPU8계약·데이터/소스/초기모델해시·실제trainer/controller/GPU와첫정상50epoch/2350batch저장계약을통과했고실제학습중이다. CIFAR/IBA재현성공이나탐지성공으로대체하지않으며최종100R/KD10·성능·전달은미완료다. 첫실제악성역할을포함한별도CPU7R감사는56역할/65phase/3250epoch/150350batch,Adam/SGD·RNG,실제제출수식/8명정확집계/연결과11점gamma선택산술을통과했다. 전체gamma독립재추론/최종100R성공은아니다. 2026-10-31 MNIST/DBA 실제100R/800역할/1358phase·67900epoch·3042500batch와KD10/470을완료했다. 독립10000/9026평가가전CA99.11/ASR30.600487480611566,후CA99.08/ASR32.35098604032794에정확일치해두성능게이트는미달이다. 실제client4기여41개·정확차감,146gamma선택산술/미달zero2,전체CPU감사와69payload strictCPU/finiteforward를통과했다. 선택모델과전체로그984파일을양쪽봉인전달하고모든sha/양쪽catalogueguard를확인했다. 새case fuba.reference.mnist.dba.s20261023.pre100.post.kd10은diagnostic만허용하며기존case/default/audit를보존했다. 전체원시phase는DISLAB에보존한다. 성공재현/탐지증거가아니며전체구현목표는미완료다. 별도stage19상태진단에서차감직후CA98.88/ASR68.3691557722136였고KD10후32.35098604여서등록된KD약화가설이지지됐다. 검증전후정수수는재사용했고새학습/모델편집은없다. 삭제전30.6005실패와실제KD10후실패는남고성공한잠복쌍은아니다. local패치validation/global합집합의행동차이를관측했지만감마수정의전체FL성공은미검증이다. 고정두역할의22global gamma검사에서100R local9.8113/global58.1132의scope위반은확인했다. 단일round zero대체집계는CA99.07/ASR16.09794로사전10기준을못넘어이수정하나의전체실행게이트는실패했다. 개선과음성을보존하고별도마지막억제자99/client4 recovery SGD/Adam100epoch비교를사전등록했다. 다른CIFAR embedding optimizer실패를다시실행하거나Adam동일수식으로부르지않는다. 마지막억제자99/client4 recovery의새SGD50epoch/2150batch는원래phase4 tensorbit재현gate를실패해B를실행하지않고중단했다. optimizer/loader·CPU·CUDA RNG는같고최대수치차이8.94e-08이지만원인은미확정이다. 이실패를보존하며입력bit일치/행동1%p gate를통과할때만미실행B50epoch를처음학습하는별도current-runtime비교를등록했다. A를재학습하거나strictbit실패를통과로고치지않는다. 별도current-runtime후속은입력bit/loader RNG/원phase4대A행동일치를통과하고A를재훈련하지않은채B50epoch/2150batch만최초학습했다. recovered ASR은A98.26058/B98.00576,실제99R대체집계는37.00421/36.58320으로두기준을실패해optimizer만으로전체학습을열지않는다. 실제A/B모델·optimizer/RNG·로그를전달했다. 2026-10-31 recovery의strict-bit 대조는8.94e-08 비트차이로실패를보존했다. 입력/loader RNG/전체평가정수수동일gate를별도통과한현재runtime B-only Adam50epoch/2150batch는SGD회복ASR98.26058 대Adam98.00576으로20%p 개선gate에실패했고실제99R대체집계도37.00421/36.58320으로10에못미쳤다. Adam/global-gamma 선택을채택하지않는다. 논문10random-seed 평균의필요조건을확인하는별도고정10행study를사전등록했다. 완료실패seed20261023을포함하고미리추출한새9개를같은Algorithm-SGD 수치코드/새초기화·IID분할/실제100R/KD10으로DISLAB에서순차계산한다. 성공시중단/실패seed제외/목록확장은금지한다. 현재준비단계이며최종성능은미측정이다. 본문Adam 실험프로필의정확재현이나D08/D15 탐지해결이아니다. 새9개CPU준비는통과했으나첫seed5129832 launch가3epoch 뒤실제PID와예약작업이사라져중단됐다. 완료phase/round는0이고종료원인은미확정이다. 원상태/3epoch/소스·입력을보존한별도운영복구는동일initial/SPLIT/숫자코드를새attempt경로에복사했다. 직접Python action을쓰는명시복구계약이며wrapper원인을확정하지않는다. 직접Python 운영복구후실제세PID/첫50epoch/3개round커밋과4R진행을확인했다. 별도첫1R CPU8역할/400epoch/18800batch·정확집계·optimizer/RNG검사가통과했다. 현재MNIST4개공식MD5/압축해제바이트도통과했다. warmup검사이며최종100R/KD10·악성성능·10행평균은미완료다. 새6R의48역할/54phase/2700epoch/125300batch,실제attacker1/defender1 제출식·정확집계·optimizer/RNG·11점gamma선택산술1개도CPU감사통과했다. 전체gamma독립추론이나최종재현성공은아니다. 첫새seed5129832의실제100R/800역할/1394phase/69700epoch·3117500batch와client4실제47기여차감/KD10/470을완료했다. 독립10000/9026평가전CA99.12/ASR23.000221582096167,후CA99.15/ASR29.016175493020164로두게이트미달이며152gamma선택산술/전체CPU감사와양쪽readonly982파일·로컬74payload strictCPU/세catalogueguard가통과했다. case fuba.algorithm_sgd.mnist.dba.s5129832.pre100.post.kd10.seed_repro20261031은diagnostic만허용한다. 기존case/default/audit를보존했다. baseline포함10행중2개완료이며다음seed4059094는GPU진입자원조건을기다린다. source/성능조건은변경하지않고기존parent가순차계속한다.
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

**묶은 폴더:** [asr_root_cause_20261022](asr_root_cause_20261022) · [fuba_corrected_20261022](fuba_corrected_20261022) · [continuation_20261023](continuation_20261023) · [multiseed_actual_fu_20261022](multiseed_actual_fu_20261022) · [FU_gpu20261020](FU_gpu20261020) · [MOVE_TO_DISLAB_20261021](MOVE_TO_DISLAB_20261021) · [stage1_fresh_20261020](stage1_fresh_20261020) · [fuba_checkpoint_recovery_20261023](fuba_checkpoint_recovery_20261023) · [FUBA_v2_s20261023_round0063](../CHECKPOINTS_FOR_REVIEW/FUBA_v2_s20261023_round0063) · [FUBA_v2_s20261023_pre_round100](../CHECKPOINTS_FOR_REVIEW/FUBA_v2_s20261023_pre_round100) · [fuba_suppression_audit_20261024](fuba_suppression_audit_20261024) · [fuba_paper_rebuild_20261024](fuba_paper_rebuild_20261024) · [FUBA_v3_s20261023_pre_round0015_stopped_verified](../CHECKPOINTS_FOR_REVIEW/FUBA_v3_s20261023_pre_round0015_stopped_verified) · [fuba_paper_flow_20261024](fuba_paper_flow_20261024) · [FUBA_v4_s20261023_pre_round0023_stopped_verified](../CHECKPOINTS_FOR_REVIEW/FUBA_v4_s20261023_pre_round0023_stopped_verified) · [fuba_paper_completion_20261024](fuba_paper_completion_20261024) · [FUBA_v5_s20261023_pre_round100](../CHECKPOINTS_FOR_REVIEW/FUBA_v5_s20261023_pre_round100) · [fuba_post_unlearning_20261025](fuba_post_unlearning_20261025) · [FUBA_v5_s20261023_pre100_post_KD10](../CHECKPOINTS_FOR_REVIEW/FUBA_v5_s20261023_pre100_post_KD10) · [fuba_execution_audit_20261025](fuba_execution_audit_20261025) · [fuba_algorithm_execution_20261025](fuba_algorithm_execution_20261025) · [fuba_optimizer_isolation_20261031](fuba_optimizer_isolation_20261031) · [fuba_radius_alignment_20261031](fuba_radius_alignment_20261031) · [fuba_reference_mnist_dba_20261031](fuba_reference_mnist_dba_20261031) · [fuba_stage_localization_20261031](fuba_stage_localization_20261031) · [fuba_dba_gamma_scope_20261031](fuba_dba_gamma_scope_20261031) · [fuba_defender_recovery_20261031](fuba_defender_recovery_20261031) · [fuba_recovery_current_ab_20261031](fuba_recovery_current_ab_20261031) · [fuba_seed_repro_20261031](fuba_seed_repro_20261031)

<a id="r03"></a>

## R03 · FedUBA 공식 배포본·논문 대응과 표본 정체 감사

**가설 한 줄: 공식 FedUBA 배포본이 논문의 실행 절차와 표본 정체를 보존하여 탐지 검증에 쓸 실제 공격 전후쌍을 제공한다.**

**판정: 공식 배포 누락·원본 ID 계약 실패 / 공격 성능 재현·탐지 사용 미검증**

[실험 시작 이유와 실제 실행 과정 읽기](../experiments/01-reproduction/R03-feduba-reproduction/README.md)

- **조건:** ity207/FedUBA@005959ab8a955f4dcf094930ce6953af8fee827b와 저자 PDF/ZIP; DISLAB CPU 원본 import 및 AST 함수 실행. stcebra/FUBA 모델과 구별.
- **정상 대조·비교:** 같은 합성32샘플의 shuffled batch1 대 sequential batch1; 고정 Arguments의 FL/FU 소유권 대 보조자료 helper 소유권; 저자 ZIP 대 Git blob.
- **결과:** 저자 ZIP9파일 모두 고정 Git blob과 동일. 두 원본 import는 utils/models 부재로 종료1. 민감도 순회 위치를 데이터 ID로 재사용하는 경로의 합성 순위 일치0/32 대 순차 대조32/32; 실제 FL/FU 공격자5/7 대 보조자료2/3 불일치 확인. 실제 공격 FL/FU·CA/ASR·탐지율은 생성하지 않았다. 논문-코드 조건과 평가 정의 차이를 기록하고 G0/G1에서 전체 학습 진입을 중단했다. 이것은 실제 공격 성공률이나 논문 공격 불가능성의 증명이 아니다.
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

**묶은 폴더:** [feduba_reproduction_audit_20261031](feduba_reproduction_audit_20261031)

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

<a id="p04"></a>

## P04 · BadFU·FedUBA 방어 개발: 표상 복원·삭제 감사·공개 기능 보존

**가설 한 줄: 실제 삭제 품질과 정상 non-IID 삭제의 효용을 보존하는 공개 기능 교정은 BadFU와 FedUBA의 활성화를 억제할 수 있다.**

**판정: H10 실제공격 실패·대조군 정정 / H11 큰정상 우선 실제실행**

[실험 시작 이유와 실제 실행 과정 읽기](../experiments/04-purification/P04-defense-development/README.md)

- **조건:** 사용자 지속 개발 지시. 명시 BadFU confirmed v1/purification_pilot,1실학습시드/재학습3쌍. 단계01은D18해시검증캐시를DISLAB CPU로연산했고새FL반복이아니다.500무라벨fit/9500heldout. 실제FedUBA는별도구현중이며미검증.
- **정상 대조·비교:** 정상19.336%전체삭제를먼저검사하고정상850과공격clean효용을같은규칙으로비교. 전체CA와각클래스/유익교정보존을분리한다. D08/D15다른FU반례를보존.
- **결과:** H1 결합 ASR5.2444%/큰정상 worstclass-5.6204pp, H2 효용실패, H3 BN/head단독 ASR100, H4 identity만 선택. H5 정렬 ASR3.4778%/세쌍CA통과지만 실제삭제 누설복원, H6 삭제감사통과/ASR100. H8 Post학생은큰정상 CA85.3579/85.6421(기준89.8)로실패했고 optimizer 단독교체를채택하지않았다. H9 public선택 alpha.0453125/.0703125에서큰정상 CA90.0526/89.8421, worstclass감소.1047/1.2618pp와기존교정90%가설을통과했다. H10 같은recipe 공격확장 rawASR100/99.7667, selected100/100으로실패; same850와추가clean/member는stop규칙상미계산. 100step/34proxy점/4ASR정수수/모델BN/optimizer/hash검산통과. 비회원대조에학생학습public500이들어간평가오류를별도정정: clean9500/원testID기반trigger8542, 440classAUC검산. H5 true-labeladv 큰정상.171865/정상850.386387/공격.834895로실패유지, H9큰정상.003071/.002138로필요조건통과유지. 원수치/실패/수치정정은모두보존한다. 1280합성추론 충실도진단에서queryraw teacher일치synthetic77.7344%/heldouttrigger3.6057%, selected19.9219%/3.4184%; heldoutASRraw99.7776/selected100이다. 256query의Post출력이[1,0,135,3,0,1,116,0,0,0]로집중됐다. 이를고유원인으로확정하지않고모든출력class동일예산의H11을별도동결했다. 동일240시작/20PGD/100학생step으로KL와Post-k/teacher-not-k목표를비교하며새큰정상부터검사한다. DISLAB 목적함수 확률항/gradient방향/포화안정성계약검산통과; 학습/효과는아직미측정이다. BadFU한시드개발이며FedUBA/독립시드/범용성/형식망각성공을주장하지않는다. H11 once task/PID21236/실제query3of30와원H5teacher해시일치를확인했다. CPU2/noCUDA이며효과는아직미측정이다.
- **non-IID에 대해 남길 교훈:** 전체CA는클래스별훼손을가릴수있고Pre표현복원은실제삭제회원구별가능성을되살릴수있었다. Post학생은유한누설기준을지켜도효용을잃을수있어실제교정기능/전체정상보존/삭제감사를분리한다. 한큰정상조건의통과는D08/D15의다른FU·시드반례해결이나trigger-family-independent탐지의증거가아니며finite MIA통과는형식적망각인증이아니다.
- **반복하지 않을 주장:** 전체CA만으로무손실/삭제보존이라고부르지않고ASR사후최저후보선택/실제타깃을fit에쓰지않는다. 완료된H1/H2를재실행하거나실패를삭제하지않는다. FUBA를FedUBA로바꾸어부르지않는다.
- **재검토 조건:** 가중치/BN/head원인분해후고정서버규칙을새프로토콜로정하고큰정상동일FU/독립시드/전체공격평가/삭제품질을함께통과해야채택한다. 각후보실패는보존후수정하고전체방어목표는계속한다.

**원문·증거:**

- [research/badfu_feduba_defense_20261031/PROTOCOL.txt](badfu_feduba_defense_20261031/PROTOCOL.txt)
- [research/badfu_feduba_defense_20261031/FREEZE.json](badfu_feduba_defense_20261031/FREEZE.json)
- [research/badfu_feduba_defense_20261031/INPUT_MANIFEST.json](badfu_feduba_defense_20261031/INPUT_MANIFEST.json)
- [research/badfu_feduba_defense_20261031/STAGE01_REPORT_KO.txt](badfu_feduba_defense_20261031/STAGE01_REPORT_KO.txt)
- [research/badfu_feduba_defense_20261031/STAGE01_RESULT.json](badfu_feduba_defense_20261031/STAGE01_RESULT.json)
- [research/badfu_feduba_defense_20261031/STAGE02_RESULT.json](badfu_feduba_defense_20261031/STAGE02_RESULT.json)
- [research/badfu_feduba_defense_20261031/COMPLETED.json](badfu_feduba_defense_20261031/COMPLETED.json)
- [research/badfu_feduba_defense_20261031/STAGE03_PROTOCOL.txt](badfu_feduba_defense_20261031/STAGE03_PROTOCOL.txt)
- [research/badfu_feduba_defense_20261031/STAGE03_FREEZE.json](badfu_feduba_defense_20261031/STAGE03_FREEZE.json)
- [research/badfu_feduba_defense_20261031/LAUNCH_RECOVERY_PROTOCOL.txt](badfu_feduba_defense_20261031/LAUNCH_RECOVERY_PROTOCOL.txt)
- [research/badfu_feduba_defense_20261031/STAGE03_REPORT_KO.txt](badfu_feduba_defense_20261031/STAGE03_REPORT_KO.txt)
- [research/badfu_feduba_defense_20261031/stage03/RESULT.json](badfu_feduba_defense_20261031/stage03/RESULT.json)
- [research/badfu_feduba_defense_20261031/stage03/COMPLETED.json](badfu_feduba_defense_20261031/stage03/COMPLETED.json)
- [research/badfu_feduba_defense_20261031/STAGE04_PROTOCOL.txt](badfu_feduba_defense_20261031/STAGE04_PROTOCOL.txt)
- [research/badfu_feduba_defense_20261031/STAGE04_FREEZE.json](badfu_feduba_defense_20261031/STAGE04_FREEZE.json)
- [research/badfu_feduba_defense_20261031/STAGE04_REPORT_KO.txt](badfu_feduba_defense_20261031/STAGE04_REPORT_KO.txt)
- [research/badfu_feduba_defense_20261031/stage04/RESULT.json](badfu_feduba_defense_20261031/stage04/RESULT.json)
- [research/badfu_feduba_defense_20261031/stage04/COMPLETED.json](badfu_feduba_defense_20261031/stage04/COMPLETED.json)
- [research/badfu_feduba_defense_20261031/stage04/SELECTION_BEFORE_TRIGGER.json](badfu_feduba_defense_20261031/stage04/SELECTION_BEFORE_TRIGGER.json)
- [research/badfu_feduba_defense_20261031/STAGE05_PROTOCOL.txt](badfu_feduba_defense_20261031/STAGE05_PROTOCOL.txt)
- [research/badfu_feduba_defense_20261031/STAGE05_FREEZE.json](badfu_feduba_defense_20261031/STAGE05_FREEZE.json)
- [research/badfu_feduba_defense_20261031/STAGE05_REPORT_KO.txt](badfu_feduba_defense_20261031/STAGE05_REPORT_KO.txt)
- [research/badfu_feduba_defense_20261031/stage05/FIT_RESULT.json](badfu_feduba_defense_20261031/stage05/FIT_RESULT.json)
- [research/badfu_feduba_defense_20261031/stage05/FIT_COMPLETED.json](badfu_feduba_defense_20261031/stage05/FIT_COMPLETED.json)
- [research/badfu_feduba_defense_20261031/stage05/INDEPENDENT_FIT_VERIFICATION.json](badfu_feduba_defense_20261031/stage05/INDEPENDENT_FIT_VERIFICATION.json)
- [research/badfu_feduba_defense_20261031/STAGE05_WAIT_PROTOCOL.txt](badfu_feduba_defense_20261031/STAGE05_WAIT_PROTOCOL.txt)
- [research/badfu_feduba_defense_20261031/STAGE05_WAIT_FREEZE.json](badfu_feduba_defense_20261031/STAGE05_WAIT_FREEZE.json)
- [research/badfu_feduba_defense_20261031/STAGE06_PROTOCOL.txt](badfu_feduba_defense_20261031/STAGE06_PROTOCOL.txt)
- [research/badfu_feduba_defense_20261031/STAGE06_FREEZE.json](badfu_feduba_defense_20261031/STAGE06_FREEZE.json)
- [research/badfu_feduba_defense_20261031/STAGE06_REPORT_KO.txt](badfu_feduba_defense_20261031/STAGE06_REPORT_KO.txt)
- [research/badfu_feduba_defense_20261031/stage06/RESULT.json](badfu_feduba_defense_20261031/stage06/RESULT.json)
- [research/badfu_feduba_defense_20261031/stage06/COMPLETED.json](badfu_feduba_defense_20261031/stage06/COMPLETED.json)
- [research/badfu_feduba_defense_20261031/STAGE07_CPU_PROTOCOL.txt](badfu_feduba_defense_20261031/STAGE07_CPU_PROTOCOL.txt)
- [research/badfu_feduba_defense_20261031/STAGE07_CPU_FREEZE.json](badfu_feduba_defense_20261031/STAGE07_CPU_FREEZE.json)
- [research/badfu_feduba_defense_20261031/STAGE07_CPU_V2_AMENDMENT.txt](badfu_feduba_defense_20261031/STAGE07_CPU_V2_AMENDMENT.txt)
- [research/badfu_feduba_defense_20261031/STAGE07_CPU_V2_FREEZE.json](badfu_feduba_defense_20261031/STAGE07_CPU_V2_FREEZE.json)
- [research/badfu_feduba_defense_20261031/STAGE07_WRAPPER_EXIT.json](badfu_feduba_defense_20261031/STAGE07_WRAPPER_EXIT.json)
- [research/badfu_feduba_defense_20261031/stage07_cpu/FAILURE.json](badfu_feduba_defense_20261031/stage07_cpu/FAILURE.json)
- [research/badfu_feduba_defense_20261031/stage05/WAIT_STOPPED_FOR_CPU_PROFILE.json](badfu_feduba_defense_20261031/stage05/WAIT_STOPPED_FOR_CPU_PROFILE.json)
- [research/badfu_feduba_defense_20261031/STAGE07_REPORT_KO.txt](badfu_feduba_defense_20261031/STAGE07_REPORT_KO.txt)
- [research/badfu_feduba_defense_20261031/stage07_cpu_v2/RESULT.json](badfu_feduba_defense_20261031/stage07_cpu_v2/RESULT.json)
- [research/badfu_feduba_defense_20261031/stage07_cpu_v2/COMPLETED.json](badfu_feduba_defense_20261031/stage07_cpu_v2/COMPLETED.json)
- [research/badfu_feduba_defense_20261031/stage07_cpu_v2/INDEPENDENT_VERIFICATION_V2.json](badfu_feduba_defense_20261031/stage07_cpu_v2/INDEPENDENT_VERIFICATION_V2.json)
- [research/badfu_feduba_defense_20261031/VERIFIER_NUMERICAL_CORRECTION.txt](badfu_feduba_defense_20261031/VERIFIER_NUMERICAL_CORRECTION.txt)
- [research/badfu_feduba_defense_20261031/STAGE08_PROTOCOL.txt](badfu_feduba_defense_20261031/STAGE08_PROTOCOL.txt)
- [research/badfu_feduba_defense_20261031/STAGE08_FREEZE.json](badfu_feduba_defense_20261031/STAGE08_FREEZE.json)
- [research/badfu_feduba_defense_20261031/STAGE08_LAUNCH.json](badfu_feduba_defense_20261031/STAGE08_LAUNCH.json)
- [research/badfu_feduba_defense_20261031/STEP_DIAGNOSIS_PROTOCOL.txt](badfu_feduba_defense_20261031/STEP_DIAGNOSIS_PROTOCOL.txt)
- [research/badfu_feduba_defense_20261031/STEP_DIAGNOSIS_FREEZE.json](badfu_feduba_defense_20261031/STEP_DIAGNOSIS_FREEZE.json)
- [research/badfu_feduba_defense_20261031/STEP_DIAGNOSIS_REPORT.txt](badfu_feduba_defense_20261031/STEP_DIAGNOSIS_REPORT.txt)
- [research/badfu_feduba_defense_20261031/step_diagnosis/RESULT.json](badfu_feduba_defense_20261031/step_diagnosis/RESULT.json)
- [research/badfu_feduba_defense_20261031/step_diagnosis/COMPLETED.json](badfu_feduba_defense_20261031/step_diagnosis/COMPLETED.json)
- [research/badfu_feduba_defense_20261031/stage08/MODELS_BEFORE_PRIVATE_EVALUATION.json](badfu_feduba_defense_20261031/stage08/MODELS_BEFORE_PRIVATE_EVALUATION.json)
- [research/badfu_feduba_defense_20261031/STAGE09_PROTOCOL.txt](badfu_feduba_defense_20261031/STAGE09_PROTOCOL.txt)
- [research/badfu_feduba_defense_20261031/STAGE09_FREEZE.json](badfu_feduba_defense_20261031/STAGE09_FREEZE.json)
- [research/badfu_feduba_defense_20261031/STAGE08_REPORT_KO.txt](badfu_feduba_defense_20261031/STAGE08_REPORT_KO.txt)
- [research/badfu_feduba_defense_20261031/stage08/RESULT.json](badfu_feduba_defense_20261031/stage08/RESULT.json)
- [research/badfu_feduba_defense_20261031/stage08/COMPLETED.json](badfu_feduba_defense_20261031/stage08/COMPLETED.json)
- [research/badfu_feduba_defense_20261031/stage08/INDEPENDENT_VERIFICATION.json](badfu_feduba_defense_20261031/stage08/INDEPENDENT_VERIFICATION.json)
- [research/badfu_feduba_defense_20261031/STAGE08_WRAPPER_EXIT.json](badfu_feduba_defense_20261031/STAGE08_WRAPPER_EXIT.json)
- [research/badfu_feduba_defense_20261031/STAGE09_REPORT_KO.txt](badfu_feduba_defense_20261031/STAGE09_REPORT_KO.txt)
- [research/badfu_feduba_defense_20261031/stage09/RESULT.json](badfu_feduba_defense_20261031/stage09/RESULT.json)
- [research/badfu_feduba_defense_20261031/stage09/COMPLETED.json](badfu_feduba_defense_20261031/stage09/COMPLETED.json)
- [research/badfu_feduba_defense_20261031/stage09/INDEPENDENT_VERIFICATION.json](badfu_feduba_defense_20261031/stage09/INDEPENDENT_VERIFICATION.json)
- [research/badfu_feduba_defense_20261031/STAGE09_WRAPPER_EXIT.json](badfu_feduba_defense_20261031/STAGE09_WRAPPER_EXIT.json)
- [research/badfu_feduba_defense_20261031/STAGE10_PROTOCOL.txt](badfu_feduba_defense_20261031/STAGE10_PROTOCOL.txt)
- [research/badfu_feduba_defense_20261031/STAGE10_FREEZE.json](badfu_feduba_defense_20261031/STAGE10_FREEZE.json)
- [research/badfu_feduba_defense_20261031/stage10/STARTED.json](badfu_feduba_defense_20261031/stage10/STARTED.json)
- [research/badfu_feduba_defense_20261031/stage10/attack_cover850/SOURCE_INPUTS.json](badfu_feduba_defense_20261031/stage10/attack_cover850/SOURCE_INPUTS.json)
- [research/badfu_feduba_defense_20261031/STAGE10_INPUT_AUDIT.json](badfu_feduba_defense_20261031/STAGE10_INPUT_AUDIT.json)
- [research/badfu_feduba_defense_20261031/HELDOUT_REFERENCE_CORRECTION_PROTOCOL.txt](badfu_feduba_defense_20261031/HELDOUT_REFERENCE_CORRECTION_PROTOCOL.txt)
- [research/badfu_feduba_defense_20261031/HELDOUT_REFERENCE_FREEZE.json](badfu_feduba_defense_20261031/HELDOUT_REFERENCE_FREEZE.json)
- [research/badfu_feduba_defense_20261031/stage10/RESULT.json](badfu_feduba_defense_20261031/stage10/RESULT.json)
- [research/badfu_feduba_defense_20261031/stage10/COMPLETED.json](badfu_feduba_defense_20261031/stage10/COMPLETED.json)
- [research/badfu_feduba_defense_20261031/stage10/INDEPENDENT_VERIFICATION.json](badfu_feduba_defense_20261031/stage10/INDEPENDENT_VERIFICATION.json)
- [research/badfu_feduba_defense_20261031/STAGE10_WRAPPER_EXIT.json](badfu_feduba_defense_20261031/STAGE10_WRAPPER_EXIT.json)
- [research/badfu_feduba_defense_20261031/heldout_reference_audit/RESULT.json](badfu_feduba_defense_20261031/heldout_reference_audit/RESULT.json)
- [research/badfu_feduba_defense_20261031/heldout_reference_audit/COMPLETED.json](badfu_feduba_defense_20261031/heldout_reference_audit/COMPLETED.json)
- [research/badfu_feduba_defense_20261031/REFERENCE_AUDIT_EXIT.json](badfu_feduba_defense_20261031/REFERENCE_AUDIT_EXIT.json)
- [research/badfu_feduba_defense_20261031/FIDELITY_DIAGNOSIS_PROTOCOL.txt](badfu_feduba_defense_20261031/FIDELITY_DIAGNOSIS_PROTOCOL.txt)
- [research/badfu_feduba_defense_20261031/FIDELITY_FREEZE.json](badfu_feduba_defense_20261031/FIDELITY_FREEZE.json)
- [research/badfu_feduba_defense_20261031/STAGE10_REPORT_KO.txt](badfu_feduba_defense_20261031/STAGE10_REPORT_KO.txt)
- [research/badfu_feduba_defense_20261031/HELDOUT_REFERENCE_CORRECTION_REPORT_KO.txt](badfu_feduba_defense_20261031/HELDOUT_REFERENCE_CORRECTION_REPORT_KO.txt)
- [research/badfu_feduba_defense_20261031/FIDELITY_DIAGNOSIS_REPORT_KO.txt](badfu_feduba_defense_20261031/FIDELITY_DIAGNOSIS_REPORT_KO.txt)
- [research/badfu_feduba_defense_20261031/fidelity_diagnosis/RESULT.json](badfu_feduba_defense_20261031/fidelity_diagnosis/RESULT.json)
- [research/badfu_feduba_defense_20261031/fidelity_diagnosis/COMPLETED.json](badfu_feduba_defense_20261031/fidelity_diagnosis/COMPLETED.json)
- [research/badfu_feduba_defense_20261031/RELATED_METHODS_NOTE.txt](badfu_feduba_defense_20261031/RELATED_METHODS_NOTE.txt)
- [research/badfu_feduba_defense_20261031/STAGE11_PROTOCOL.txt](badfu_feduba_defense_20261031/STAGE11_PROTOCOL.txt)
- [research/badfu_feduba_defense_20261031/STAGE11_FREEZE.json](badfu_feduba_defense_20261031/STAGE11_FREEZE.json)
- [research/badfu_feduba_defense_20261031/STAGE11_OBJECTIVE_VERIFICATION.json](badfu_feduba_defense_20261031/STAGE11_OBJECTIVE_VERIFICATION.json)
- [research/badfu_feduba_defense_20261031/STAGE11_OBJECTIVE_RECEIPT_CORRECTION.txt](badfu_feduba_defense_20261031/STAGE11_OBJECTIVE_RECEIPT_CORRECTION.txt)
- [research/badfu_feduba_defense_20261031/STAGE11_LAUNCH.json](badfu_feduba_defense_20261031/STAGE11_LAUNCH.json)
- [research/badfu_feduba_defense_20261031/stage11/STARTED.json](badfu_feduba_defense_20261031/stage11/STARTED.json)
- [research/badfu_feduba_defense_20261031/stage11/benign_big19336/SOURCE_INPUTS.json](badfu_feduba_defense_20261031/stage11/benign_big19336/SOURCE_INPUTS.json)
- [research/badfu_feduba_defense_20261031/STAGE11_VERIFICATION_PROTOCOL.txt](badfu_feduba_defense_20261031/STAGE11_VERIFICATION_PROTOCOL.txt)
- [research/badfu_feduba_defense_20261031/STAGE11_VERIFICATION_FREEZE.json](badfu_feduba_defense_20261031/STAGE11_VERIFICATION_FREEZE.json)
- [research/badfu_feduba_defense_20261031/DEVELOPMENT_MODEL_KO.txt](badfu_feduba_defense_20261031/DEVELOPMENT_MODEL_KO.txt)

**묶은 폴더:** [badfu_feduba_defense_20261031](badfu_feduba_defense_20261031)

