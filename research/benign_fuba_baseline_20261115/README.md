# 정상 연합학습과 참여자 삭제 기준선

**가설** MNIST IID에서 정상 참여자 4의 역사적 FedAvg 기여 차감과 KD 복구를 적용하면, 유지 참여자로 처음부터 재학습한 경우와 정상 시험 정확도 차이가 2%p 이내다.

관련 카드 **R01, R02, D08, D15**. 새 관측은 동일한 초기 모델·IID 분할·참여 순서에서 정상 FL, 기여 차감 후 KD, 유지 참여자 재학습의 정수 정답 건수와 클래스별 혼동 행렬이다. 재학습에서는 매 라운드의 원 참여자 명단에서 요청자만 제외하고 나머지 가중치를 다시 정규화한다. 정확도 차이는 정상 데이터에서의 효용으로 해석한다. D08의 큰 정상 non-IID 탈퇴 반례와 D15의 시드 간 겹침은 미검증이며 이 실험으로 탐지 임계값을 정할 수 없다.

기본 프로필은 독립 초기화 한 번, 20라운드, 라운드당 8명, 고객별 2에폭, 배치 64, 샤드당 3000개의 정상 MNIST 표본이다. 별도 `paper-scale` 프로필은 100라운드와 고객별 50에폭을 사용한다. 차감에는 정상 FL에서 실제 적용된 참여자 4의 가중 델타를 사용하고, KD 복구는 정상 FL 모델을 교사로 하며 유지 참여자 5의 영상만 사용한다. KD는 10에폭이다. 교사에 요청자의 영향이 남을 수 있어 KD의 보장 범위는 경험적 효용이다. 2%p 기준은 이번 정상 효용 비교를 위해 고정했다.

데이터·유한값·참여자 원장·모델 해시·독립 평가 검사를 통과해야 결과를 사용한다. 오류가 발생하면 새 출력 경로에 실패를 기록한다. 정확도 차이가 2%p를 넘으면 동일 실행의 결과를 그대로 보고한다. 기존 정상 모델이나 공격 모델을 학습 시작점으로 사용하지 않는다.

```powershell
$py = 'C:/Users/DISLAB/AppData/Local/Programs/Python/Python312/python.exe'
$raw = 'C:/Users/DISLAB/Documents/antigravity/dazzling-lovelace/FUBA/data/MNIST/raw'
$out = 'D:/BENIGN_FUBA_BASELINE_20261115/baseline-new'
& $py benchmark.py --mnist-raw $raw --output $out
& $py evaluate.py run --mnist-raw $raw --output $out
```

`benchmark.py`는 빈 출력 경로에서 정상 시점, KD 복구, 유지 참여자 재학습의 세 `.pt`와 결과·참여자·데이터/코드 식별 기록을 쓴다. 별도 프로세스의 `evaluate.py run`은 원래 CPU 런타임에서 10,000장 전체 시험을 재계산한다. `counts`는 기존 before/after JSON 평가 영수증의 정수 분자·분모에서 CA와 ASR을 검산하며 PyTorch를 사용하지 않는다. 정상 기준선은 깨끗한 입력 전체의 CA를 보고한다.

논문의 정확도 항목은 BA로 표기된다. KD 열의 MNIST·DBA 10시드 평균은 BA 99.30% → 99.10%, ASR 7.20% → 82.90%이고 CIFAR-10·IBA는 BA 85.10% → 84.00%, ASR 8.60% → 60.50%다. 보존된 DISLAB v6 및 v7의 정수 집계를 `counts`로 재계산해 기존 독립 평가의 표시값과 일치함을 확인했다. [FUBA 논문 Table I](https://ieeexplore.ieee.org/document/11231135/)

## DISLAB 실행 결과

| 모델 | 정상 정답 수 | 정상 정확도 |
|---|---:|---:|
| 정상 FedAvg 20라운드 | 9,868 / 10,000 | 98.68% |
| 참여자 4 기여 차감 후 KD 10에폭 | 9,859 / 10,000 | 98.59% |
| 참여자 4 제외 후 처음부터 재학습 20라운드 | 9,871 / 10,000 | 98.71% |

KD와 유지 참여자 재학습의 차이는 −0.12%p로 2%p 효용 기준을 통과했다. 코드와 데이터 SHA256, 실제 참여 라운드 8건, KD 10에폭, 세 `.pt`의 SHA256과 strict CPU 로드, 10,000장 정답 수 및 혼동 행렬 일치를 확인했다. 참여자 가중 델타를 별도 프로세스에서 다시 학습해 검산하는 범위는 포함하지 않았다. 이번 수치의 범위는 CPU에서 실행한 20라운드·2로컬 에폭, IID 한 시드다. 100라운드 프로필은 미실행이다.

세 모델과 원 실행 로그는 DISLAB의 `D:/BENIGN_FUBA_BASELINE_20261115/baseline`에 있다. 네 검토 기록은 DISLAB 원본과 SHA256이 일치한다. [실행 프로필](evidence/profile.json) · [학습 로그](evidence/events.jsonl) · [결과](evidence/result.json) · [독립 평가](evidence/verified.json)
