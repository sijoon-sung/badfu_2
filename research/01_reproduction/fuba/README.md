# FUBA 첫 독해와 코드 검토

이 연구의 정식 이름은 **FUBA Backdoor Federated Learning via Federated Unlearning**이다. [IEEE 공식 초록](https://ieeexplore.ieee.org/document/11231135/)과 [저자 공개 저장소](https://github.com/stcebra/FUBA)를 기준으로 한다. BadFU와 같은 이름의 공격으로 합치지 않는다.

## 먼저 확인한 공격 구조

공식 초록은 Adv-attacker가 백도어를 주입하고 Adv-defender가 이를 억제하다가, 후자의 기여를 삭제해 공격을 드러내는 역할 분담을 설명한다. BadFU가 위장 샘플의 기여를 삭제하는 것과 비교할 축이다. 두 역할은 공격 체계 내부의 역할이며 Adv-defender는 정직한 방어자가 아니다.

초록의 FU 방법 독립성 주장을 보편 정리로 해석하지 않는다. 원문 전체와 보충자료를 이번에 확보하지 못해 상세 표·각주·이론 가정의 재확인이 남아 있다. 옛 리뷰의 숫자를 새 검증 결과로 사용하지 않는다.

## 이번 코드에서 확인한 문제

| 항목 | 보존 코드 위치 | 확인한 사실 | 후속 확인 |
|---|---|---|---|
| L2 항 | train_method_iba.py 133행 | WITH_L2 분기에서 `0 * l2_loss` | 실행한 가지와 논문 버전 대응 |
| gamma 선택 | 같은 파일 309–327행 | 후보 0.1…1.0의 인덱스 1이면 평가값 0.2인데 재구성은 0.1 | 점수와 실제 제출 모델 대응 |
| Topk | unlearn_method/retrain.py 456–464행 | 선택된 모델을 일반 평균으로 다시 덮어씀 | 이 코드로 얻은 방어 수치의 해석 |
| FU 중 공격 | retrain.py의 local_train와 attacker_train | backdoor 참여자는 다시 악성 학습을 수행 | 기존 독성의 드러남과 새 주입 분리 |
| 시험 자료 | train_main.py 103행과 gamma 탐색 | 전달된 testloader가 공격 강도 선택에 사용됨 | 로컬 공격 보정 자료로 대체한 대조 |

L2 0과 gamma 재구성은 [공식 IBA 소스](https://github.com/stcebra/FUBA/blob/main/train_method_iba.py)에서도 같은 표현을 확인했다. 나머지는 보존 소스에 대한 관측이며 논문 표를 만든 비공개 버전까지 같다고 단정하지 않는다. [작은 CPU 검사](../badfu/code_contract_results.json)에 helper 계산과 정적 관측을 기록했다.

## 처음 분리할 실험

같은 FL 종료 모델과 삭제 요청에서 **FU 중 공격자가 정직하게 갱신하는 조건**과 **공개 코드의 악성 재학습 조건**을 나란히 둔다. 방어의 적용 시점도 FL 중·FU 중·FU 후로 구분한다. 한 조건의 성능을 두 공격 경로 모두의 방어로 주장하지 않는다.

[전체 검증 조건](../BASIC_VALIDATION.md) · [방어 후보의 적용 범위](../../02_purification/FOUNDATION_HYPOTHESES.md)
