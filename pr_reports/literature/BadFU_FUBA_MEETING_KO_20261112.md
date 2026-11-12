# BadFU와 FUBA의 공통 억제 제거 기제

교수 미팅 자료 정정 · 2026-11-12 · R01/R02, D08, D19/D20/D23–D25, T03

## 발표에서 먼저 보여줄 대응

| 과정 | BadFU | stcebra/FUBA |
|---|---|---|
| 백도어 심기 | 한 공격 참여자의 독성 표본이 트리거와 목표 라벨을 연결 | Adv-attacker의 로컬 기여가 백도어를 주입 |
| 학습 중 억제 | 같은 참여자의 위장 표본이 같은 트리거에서 원래 라벨을 지지 | 별도 Adv-defender의 로컬 기여가 백도어 행동을 억제 |
| 삭제 대상 | 실제 학습에 사용된 위장 표본 | Adv-defender 참여자의 기여 |
| 서버 역할 | 정상 FU 절차로 요청 표본의 영향을 제거 | 정상 FU 절차로 요청 참여자의 영향을 제거 |
| 공통 효과 | 백도어 기여는 남고 억제 기여가 사라지면서 특정 입력의 공격 목표 예측이 증가 | 같은 억제 제거 구조 |

FUBA에서 Adv-defender는 공격 시나리오에 협력하는 참여자다. 서버의 강건 집계와 이상 탐지는 별도의 실제 방어다. BadFU는 표본 수준, FUBA는 참여자 수준에서 이 구조를 구성한다. 이 대응은 논문의 행동 수준 설명이다. FC PCA 방향이나 동일한 내부 좌표가 두 논문에서 필요하다는 주장과는 별도다. [BadFU §IV–V](https://arxiv.org/html/2508.15541v1#S4) · [FUBA 본문 Fig. 1(b), Algorithms 1–2, pp. 2895–2898](https://ieeexplore.ieee.org/document/11231135/) · [FUBA 고정 저자 코드](https://github.com/stcebra/FUBA/tree/bc233610aca36e1647d0c815597cc7148292139d)

## 논문이 보고한 수치

CIFAR-10, 단위 %. CA/BA는 clean 정확도, ASR은 알려진 트리거에서 목표 예측 비율이다.

| 원문 조건 | 삭제 전 CA 또는 BA / ASR | 해당 삭제 후 CA 또는 BA / ASR |
|---|---:|---:|
| BadFU BadNet · 전체 재학습 | 84.84 / 21.55 | 83.90 / 99.32 |
| BadFU BadNet · FedEraser | 84.84 / 21.55 | 83.19 / 90.76 |
| BadFU BadNet · 정상 삭제 | 84.84 / 21.55 | 81.29 / 10.22 |
| FUBA+IBA · 전체 재학습 | 85.10 / 8.60 | 85.00 / 73.10 |
| FUBA+IBA · FedEraser | 85.10 / 8.60 | 84.20 / 72.90 |
| FUBA+IBA · KD | 85.10 / 8.60 | 84.00 / 60.50 |

독립 논문 조건의 대표 행이다. 같은 모델·분할·트리거를 맞춘 우열 비교는 아니다. FUBA 논문의 결과는 10개 시드 평균으로 보고됐다. [BadFU Tables I, V](https://arxiv.org/html/2508.15541v1#S7) · [FUBA Table I 및 §IV-A, pp. 2899–2900](https://ieeexplore.ieee.org/document/11231135/)

FUBA Table V의 CIFAR-10·IBA·Dirichlet α=0.1에서 삭제 전 ASR은 **6.90%**였다. 정상 1명 삭제는 FedEraser/KD 각각 **7.00/6.50%**, 정상 3명은 **6.30/3.30%**였다. Adv-defender만 삭제하면 **70.50/56.20%**, Adv-defender와 정상 3명을 함께 삭제하면 **71.10/53.60%**였다. 저자가 트리거와 삭제 역할을 알고 측정한 활성화 비교다. 서버가 트리거를 모를 때 정상과 공격을 정확히 분류했다는 결과는 아니다. [FUBA Table V, p. 2903](https://ieeexplore.ieee.org/document/11231135/)

실제 서버 방어 비교에서 BadFU Median은 ASR **6.55→96.33%**였다. FUBA+IBA Median은 **9.30→69.30% / 56.20%**였다(FedEraser/KD). BadFU는 Neural Cleanse도, FUBA는 B3D·MNTD·FLDetector·FLAME·BackdoorIndicator·AlignIns·MASA 등도 시험했다. 두 논문의 방어 결과는 각자 설정의 잔여 ASR로 읽는다. [BadFU Tables VI–VII](https://arxiv.org/html/2508.15541v1#S7.SS7) · [FUBA Table II, p. 2900](https://ieeexplore.ieee.org/document/11231135/)

## DISLAB 재현과 저장 라운드

| 자체 실행 | 전 CA / ASR (%) | 후 CA / ASR (%) | 판정 |
|---|---:|---:|---|
| BadFU 20261020 · 전체 재학습 | 88.23 / 16.14 | 88.15 / 99.99 | 활성화 방향 재현 |
| BadFU 20261023 · 전체 재학습 | 90.38 / 14.29 | 90.46 / 100.00 | 활성화 방향 재현 |
| FUBA v5 · 100R→KD10 | 78.58 / 28.69 | 78.95 / 28.42 | 진단 |
| FUBA v6 · 100R→KD10 | 77.80 / 12.81 | 78.03 / 14.54 | 진단 |
| FUBA v7 · 100R→KD10 | 77.76 / 10.56 | 77.76 / 16.74 | 진단 |

FUBA v5/v6/v7은 실행 해석이 다른 단일 시드 프로필이다. 독립 학습 시드 세 개로 세지 않는다. v7의 실제 FL100과 KD10은 완료했고, 동일 고정 생성기로 pre/post의 10,000장 clean 및 9,000장 비목표 평가를 독립 재현했다. 자체 사전 CA≥80%, pre ASR≤10%, post ASR≥60% 기준에 미달했다. [R01 BadFU 감사](../../research/badfu_algorithm_audit_20261023/README.md) · [R02 FUBA 완료 및 판정](../../experiments/01-reproduction/R02-fuba-reproduction/README.md)

| FUBA v7 저장 시점 | CA (%) | ASR (%) |
|---|---:|---:|
| FL 5R | 65.98 | 2.29 |
| FL 20R | 76.23 | 5.71 |
| FL 40R | 77.36 | 10.04 |
| FL 60R | 77.77 | 10.66 |
| FL 80R | 77.14 | 4.49 |
| FL 100R | 77.76 | 10.56 |
| Adv-defender 기여 차감 후 | 77.52 | 14.47 |
| KD 10 epoch 후 | 77.76 | 16.74 |

앞의 FL 행은 각 저장 라운드 평가다. 마지막 세 단계는 동일 생성기를 사용하는 FU 전후 비교로 표시한다. 100R/차감/KD10의 실제 목표 예측 수는 950/1,302/1,507개이며 분모는 각각 9,000장이다. 중간 행은 학습 라운드에 따라 생성기 상태가 달라질 수 있다. 로컬 봉인 FUBA v7 패킷 `evaluation/round*.json`, `evaluation/after_subtraction.json`, `FINAL_INDEPENDENT_EVALUATION.json`과 R02 최종 대조에서 확인했다. [R02 FUBA 판정](../../experiments/01-reproduction/R02-fuba-reproduction/README.md)

## 탐지 실험과 해석

- **D20.** BadFU 두 공격과 정상 네 조건에서, 실제 트리거를 받지 않는 네 경로 탐색이 최저 공격–최고 정상 간격을 20.56→30.44%p로 넓혔다. FUBA v7 진단쌍의 전환은 기본 47/900, 네 경로 49/900이었다. 승인된 성공 FUBA 공격 전후쌍과 같은 구현의 큰 정상 FU 대조가 없어 이 진단 수치로 일반화를 판정할 수 없다. [D20 원보고서](../../research/blind_route_detector_v2_20261110/REPORT_KO.txt)
- **D19.** 과거 FUBA 진단의 FC-PCA 점수는 억제 역할 삭제 3.417671, 정상 삭제 3.599358이었다. 각 쌍의 346조건에서 기준 초과는 0이었다. 이전 진단쌍과 작은 정상 삭제를 비교한 결과다. [D19 원보고서](../../research/fuba_projection_check_20261025/REPORT_KO.txt)
- **D24.** BadFU의 새 공개 이미지 A/B에서 공격 말단이 모든 정상보다 높았다. 고정 5건 초과 기준은 각 묶음에서 정상 한 건씩을 경보했다. 10R B에서는 큰 정상 19.336%와 공격 이력이 6건으로 겹쳤다. 같은 FC 층에서 제거량과 차원을 맞춘 무작위 대조 중 한 반복은 두 묶음에서 정상 0/4, 공격 2/2였다. [D24 라운드·같은 층 대조](../../research/badfu_fc_pca_matched_control_20261112/REPORT_KO.txt)
- **D25의 BadFU 부분.** 같은 이미지에 약한 두 변환을 적용해 전환의 공동 유지율을 보았다. 보정 분할 1은 큰 정상 경보 0/2·공격 2/4, 분할 2는 큰 정상 경보 2/2·공격 4/4였다. 두 공격 시드에 A/B를 적용했으므로 네 평가는 독립 공격 실행 네 번이 아니다. [D25 원보고서](../../research/cross_view_transition_20261112/REPORT_KO.txt)
- **D08과 T03.** 같은 잔류 참여자 개입의 점수에서 공격 0.75848이 큰 정상 0.75525와 0.76188 사이에 있었다. 알려진 BadFU 실제 트리거의 6,754개 전환은 FC 직교항을 제외해도 모두 남았다. 하나의 행동 변화나 내부 방향을 공통 원인으로 채택할 근거는 부족하다. [D08 원보고서](../../research/active_fu_pairs_20261022/REPORT_KO.md) · [T03 원보고서](../../research/topdown_mechanism_20261110/REPORT_KO.txt)

## 진행 판정과 방법론의 차이

**FUBA 재현은 실패했다.** 실행 완료와 공격 재현 판정을 구분한다. MNIST/DBA 두 시드의 실제 100R ASR은 30.60%와 23.00%로 사전 억제 기준 10%를 초과했고, KD10 후 ASR은 32.35%와 29.02%로 활성화 기준 60%에 미달했다. 20261023의 차감 직후 68.37%는 같은 쌍의 실제 삭제 전 억제와 KD10 후 활성화를 입증하지 않는다. 감사한 FUBA 완료쌍 다섯 개 중 적격은 0개다. [R04 적격성 감사](../../research/fuba_pair_admission_audit_20261112/REPORT_KO.txt) · [R05 단계별 검산](../../research/fuba_mnist_suppression_timeline_20261112/REPORT_KO.txt)

| 비교 대상 | 관측 단위와 판단 | 우리 작업의 차이 |
|---|---|---|
| UBA-Inf | 언러닝 전후 모델에 백도어 스캐너 적용 | 같은 입력의 삭제 전후 전환을 전역 모델 두 개에 연결해 확인한다. 전후 검사 자체에는 선행이 있다. |
| MASA | 학습 중 로컬 모델의 개별 언러닝 반응으로 집계 전 검사 | 실제 삭제 요청 전후의 글로벌 모델이 대상이다. |
| EX-RAY와 FeatureRE | 모델 내 특징 교환 또는 특징 공간 제약으로 백도어 탐색 | 삭제 전후의 특징 추출부와 분류기를 교차한 네 경로를 후보 선택에 함께 사용하고, 최종 전환은 편집하지 않은 원래 두 모델에서 확인한다. 공유 특징 채널 좌표를 가정한다. |
| CSO | 클래스 고유 특징에 직교하도록 탐지 통계 최적화를 제약 | FC PCA는 전환 복귀를 살피는 별도 진단이었다. 같은 FC 층의 무작위 대조 결과 때문에 PCA 고유의 검출 이득은 입증되지 않았다. |

[D20 비교 문헌과 좌표 가정](../../research/blind_route_detector_v2_20261110/LITERATURE_AND_SCOPE.txt) · [R04 선행연구 원문](../../research/fuba_pair_admission_audit_20261112/REPORT_KO.txt)

**실험으로 확인한 차이는 같은 탐색 예산에서 네 경로 조건을 추가한 효과다.** BadFU 두 공격과 정상 네 조건에서 최저 공격과 최고 정상의 전환율 간격은 20.56%p에서 30.44%p로 넓어졌다. 실제 트리거와 실제 목표는 탐색에 넣지 않았다. 이 값은 고정 시험의 전환율 간격이다. D23의 정상 보정 판정에서는 기본 탐색과 네 경로 모두 보류 큰 정상 한 건에 경보했다. 따라서 입증된 범위는 조건부 전환 후보를 찾는 탐색의 개선까지다. 독립 요청에서 같은 오경보율로 얻은 검출 이득과 FUBA로의 일반화는 미확인이다. [D20 동등 예산 비교](../../research/blind_route_detector_v2_20261110/REPORT_KO.txt) · [D23 정상 보정 비교](../../research/four_routes_pca_decision_20261112/REPORT_KO.txt)

**다음 비교의 판정 단위는 삭제 요청이다.** 현재 검증된 BadFU는 탐색법 평가에 쓸 수 있다. 공통 공격 판별은 검증된 별개 계열의 전후쌍과 동일 FU의 큰 정상 non-IID 삭제를 요구한다. 독립 학습 및 삭제 요청을 보류하고 정상으로 경보선을 고정한 뒤, 기본 탐색과 네 경로의 검출을 같은 정상 오경보 조건에서 비교한다. D08의 정상–공격 순위 역전과 D24의 10R 동률처럼 정상 겹침이 재현되거나 검출 이득이 없으면 공통 판별 주장을 채택하지 않는다. 이는 미검증 평가 계획이다. [D08 반례](../../research/active_fu_pairs_20261022/REPORT_KO.md) · [D24 보류 비교](../../research/badfu_fc_pca_matched_control_20261112/REPORT_KO.txt)
