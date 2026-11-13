실제 트리거를 받지 않고 삭제 후 전환 입력을 찾는 연구용 탐색기를 구현하고 DISLAB에서 계산했다. 전후 body/head의 네 경로를 동시에 요구하면 동등 예산의 native 전후 탐색보다 큰 정상 삭제와의 간격이 커진다는 가설을 검사했다. 관련 카드는 D20, D02/D06/D07/D08/D15/D17/D19/T02/T03/R02/R03이다.

| 고정 시험 조건 | 기존 전후 탐색 | 새 네 경로 탐색 |
|---|---:|---:|
| 정상 19.336% 삭제 | 12.33% | 7.89% |
| 정상 22.790% 삭제 | 9.67% | 8.89% |
| 정상 850개 삭제 | 9.11% | 10.56% |
| 감염 모델의 정상 850개 삭제 | 10.11% | 10.89% |
| BadFU 시드 20261023 | 32.89% | 41.33% |
| BadFU 시드 20261020 | 41.44% | 58.89% |
| stcebra/FUBA v7 진단 | 5.22% | 5.44% |
| ity207/FedUBA 정상 FU | 13.67% | 14.56% |
| ity207/FedUBA minus 진단 | 32.33% | 33.22% |
| ity207/FedUBA plus 진단 | 34.11% | 33.22% |

각 수치는 별도 시험 입력 900개에서 `x는 원모델 전후 정답, T(x)는 원 pre 정답·원 post 선택 목표 오답`인 비율이다. 공격 확률·TPR·FPR이 아니다. 모든 목표/입력조건 선택은 calibration에서 끝내 봉인한 뒤 시험했다. 실제 목표·trigger·생성기·공격 역할은 탐색 입력이 아니었다.

BadFU 공격 최솟값과 정상 최댓값의 간격은 **20.56→30.44%p**, 개선 **9.89%p**다. 사전 기준 `새 간격>0, 개선≥5%p`를 통과했다. 주 탐색은 508.4초, valid baseline 6개는 바이트 그대로 재사용하고 54개를 새로 최적화했다. 선택 후 예산/방법 조정은 없었다.

구현은 [route_core.py](route_core.py)의 `four_routes`, `train`, `score`다. 입력변환만 학습하고 모델 가중치/BN은 고정한다. 교차 함수는 조건을 발견하는 제약이고, 최종 검사는 원모델 두 함수만 쓴다. 연구용 출력은 선택 조건·목표·전환 사례 수와 `calibration_required`다. CIFAR10/선언된 세 architecture·정규화 계약을 지원하는 프로토타입이며 임의 데이터셋용 완성 제품이 아니다.

필요한 좁힘은 명확하다. 두 강한 BadFU 조건 모두 mask가 선택됐다. 정상 네 조건도 각각 9개 원클래스에 전환이 존재했다. FUBA에는 성공 잠복쌍과 같은 구현의 큰 정상 FU 대조가 없고, FedUBA에도 이번에는 작은 정상 요청만 있다. D08/D15의 non-IID 반례와 T02의 정상 희귀도메인 반례는 해결됐다고 주장하지 않는다. 공유 채널 좌표 가정·변형 예산의 의미보존 가정과 [선행연구 및 좌표 반례](LITERATURE_AND_SCOPE.txt)를 포함해 평가해야 한다. 최초성, 모든 trigger 계열, 운영 판정은 미검증이다.

실제 검사 결과는 [독립 native 검산](remote_results/VERIFIED.json), [60개 파생 payload CPU 검사](remote_results/CPU_PAYLOAD_AUDIT.json), [최종 상태/원모델 15개 해시](remote_results/FINAL_TERMINAL.json), [로컬 전달 확인](LOCAL_DELIVERY_VERIFIED.json)에 있다. 20개 정수 count와 원클래스별 count가 정확히 일치했다. 모든 gradient나 모든 calibration 후보를 독립 재추론한 것은 아니다.

v1 hook 덮어쓰기 오류, pre-CNN 자원 정지, 원 검산기의 빈 배치 오류를 보존했다. 완료 주 탐색은 반복하지 않았고 새 검산기만 빈 배치를 건너뛰어 완료했다. 원 controller의 failed 상태는 수정하지 않았다. 기존 case/default/old queue와 모델 payload는 보존했다. [전체 보고서](REPORT_KO.txt), [사전 프로토콜](PROTOCOL.txt), [수정 프로토콜](CORRECTION_PROTOCOL.txt), [검산 복구](VERIFIER_RECOVERY_PROTOCOL.txt)를 함께 검토한다.
