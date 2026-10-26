# 관련 논문이 설명하는 실패와 우리 실험의 차이

아래 원문·공식 구현은 이번 정리에서 다시 확인했다. 논문이 직접 평가한 것과 우리 실패에 연결한 해석을 분리한다. 다른 위협 모델에서 작동했다는 사실은 우리 조건의 성공도 실패도 대신하지 않는다.

| 방법과 확인 위치 | 논문·저자의 실제 판단 | 우리 기록과 연결되는 부분 | 자체 검증 상태 |
|---|---|---|---|
| [BadFU](https://arxiv.org/html/2508.15541v1#S7.SS7) §VII-G, Tables VI/VII | 시험한 조건에서 Median·Trimean 뒤에도 삭제 후 공격이 활성화되고 NC 지표에 미탐·오탐이 관측됨. FL에서 패턴이 덜 두드러진다는 설명은 possible explanation | 방어 단계와 잠복/활성 상태를 기록해야 함. 저자 결과를 우리 NC 실패로 바꾸지 않음 | 공격·코드 계열과 조정 실험은 존재. 우리 조건의 정식NC/Median·Trimean 비교는 별도 확인 필요 |
| [Neural Cleanse 공식 구현](https://github.com/bolunwang/backdoor) README Reverse Engineering/Anomaly Detection | 타깃별 역합성 트리거의 작은 크기 이상치를 검사. 입력·전처리·최적화 설정 오류가 성능을 바꿀 수 있음을 저자가 경고 | 우리 고정32패치·차분 최적화는 이 구현의 재현이 아님. 탐색 실패와 이상치 점수 실패를 분리할 필요 | 공식 재현을 확인하지 못함. 우리 패치 실험만으로 실패 주장 불가 |
| [Fine-Pruning](https://arxiv.org/abs/1805.12185) Abstract | 정교한 공격에서 pruning·fine-tuning 각각만으로 불충분한 사례와 결합 방법을 평가 | 우리 SVD 제거·특징 마스킹을 결합 정화 전체와 동일시하면 안 됨 | 변형 기준선 코드는 있음. 공식 결합 방법 재현은 확인 못 함 |
| [MASA](https://arxiv.org/html/2411.01040v1#S3) §3, model fusion, Table4 | 정상 자료에서 개별 망각 동역학을 관측하고 Non-IID 로컬 모델 차이를 융합으로 완화. 융합 제거 시FPR 증가를 보고 | 정상 학습 난이도·로컬 분포가 진단 반응을 바꾼다는 문제와 연결. 우리 R/F CE감소 비율의 실패 원인을 직접 증명한 논문은 아님 | 소스가 있어도 공식실행 근거를 확인한 것은 아님. 우리 조건에서는 미검증 |
| [DeepSight](https://www.ndss-symposium.org/wp-content/uploads/2022-156-paper.pdf) Abstract, Introduction | 다수와 다른 정상 모델을 이상치로 제외하면 효용을 해칠 수 있다고 지적. 여러 내부·출력 관측과 군집·clipping을 결합 | 우리 단일 노름·코사인 점수 중첩과 문제의식은 관련됨. 우리 위장 삭제에서의 실패 원인을 직접 실험한 것은 아님 | 정식 비교 미확인 |
| [UnlearnGuard](https://arxiv.org/html/2501.17396v1#S4) §4, Theorem1 | FU중 새 악성 업데이트를 예측·검사. 근접성 정리는 FL의 악성 참여자가 모두 탐지됐다는 조건 포함 | 기존 독성이 남은 상태의 정직한 삭제는 별도 문제. 이력이 있다는 이유로 보장을 승계할 수 없음 | 원문 검토. 우리 잠복 삭제 조건의 공식실행 미확인 |
| [FedEraser](https://arxiv.org/abs/2012.13891v3) Abstract | 과거 갱신 저장과 보정을 이용해 FU 재구성 비용을 줄임 | 단순 누적 기여 차감은 같은 연산이 아님. 재학습 근접성과 남은 독성의 안전성도 별도 | 저자 계열FU와 조정된1단계 등을 구분. 차감 대용 실패를 FedEraser 실패로 세지 않음 |
| [SAU](https://proceedings.neurips.cc/paper_files/paper/2023/hash/520425a5a4c2fb7f7fc345078b188201-Abstract-Conference.html) Abstract | 작은 정상 자료와 모델 간 공유 적대 예제를 이용하는 이중 최적화 정화 | 두 모델·적대 탐색 자체가 신규성 근거는 아님. 우리 전후 정보의 추가 이득은 같은 정화·예산에서 검증 필요 | 우리 공식비교 미실험으로 기록 |

## 주변 논문에서 가져올 수 있는 판단의 범위

1. **정상 이질성이 탐지 통계를 바꿀 수 있다:** MASA·DeepSight가 직접 다루는 문제다. 우리 FC·Conv 오탐의 수치적 원인은 우리 대응 실험으로 확인해야 한다.
2. **방어를 적용하는 단계가 중요하다:** 학습중 업데이트 필터, FU중 새 업데이트 검사, 삭제후 정화는 다른 비교군이다.
3. **원문 방법의 구성 요소를 일부 구현한 것과 정식 방법 재현은 다르다:** 공식 코드를 보통의 활성 백도어·정상 모델에서 먼저 확인할 필요가 있다.
4. **추가 정보의 가치가 비교 대상이다:** 전후 모델·학습 이력·정상 자료·참여자 협력 중 무엇을 추가로 썼는지 비용과 함께 기록해야 한다.

FUBA·SubID·FLAME·BackdoorIndicator·FedREDefense 등에 대한 기존 리뷰도 [리뷰 색인](../review_BadFU_defend/docs/paper_reviews/README.md)에 있다. 이번 원문 재확인 표에 없는 세부 수치·가정은 기존 리뷰에서 자동 승계하지 않았다. FUBA의 이번 학습·생성기 조건은 [실행 protocol](evidence/remote/artifacts/fuba_cifar10_s42/protocol.json)을 우선 사용했다.
