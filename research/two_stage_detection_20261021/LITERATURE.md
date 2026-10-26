# 두 단계 탐지와 연결한 선행연구 근거

기준일 2026년 10월 21일. 원문 또는 저자 구현을 조회한 범위와 이번 자체 실행을 구분한다. 이번 파일럿에서 새로 실행한 것은 자체 패치 기여 기준선이며 아래 방어 논문의 공식 재현이 아니다.

| 연구 | 일차 출처와 확인 위치 | 두 단계 탐지에서 비교할 대상 | 이번 확인 상태 |
|---|---|---|---|
| BadFU Lu 등 2025 | [arXiv v1](https://arxiv.org/html/2508.15541v1) IV V VII G절 Table VII | 같은 참여자 P C와 위장 삭제 잠복 구조 | 원문 확인 기존 체크포인트 재사용 |
| FUBA Sheng 등 | [저자 코드](https://github.com/stcebra/FUBA) README Abstract와 Usage | 분리된 주입 억제 참여자와 요청 | 저자 설명 확인 기존 체크포인트 재사용 논문 수치 새 검증 제외 |
| FedUBA Chen 등 2026 | [저자 공개 논문](https://www.chenwang.net.cn/publications/FedUBA-TDSC26.pdf) III V절 식 6 8 Fig 9 | 학습 조작 없는 삭제 단계 요청 조작 | 원문 17쪽 확인 공식 대응 체크포인트 미실행 |
| UBA-Inf Huang 등 2024 | [USENIX Security 24](https://www.usenix.org/conference/usenixsecurity24/presentation/huang-zirui) 논문 초록과 서지 | 위장 삭제로 백도어 활성화하는 선행 개념 | 학회 일차 출처 확인 이번 공식 실행 없음 |
| Neural Cleanse Wang 등 2019 | [저자 구현](https://github.com/bolunwang/backdoor) visualizer 및 anomaly detection 설명 | 전역 모델의 트리거 이상 검사 | 저자 구현 설명과 BadFU의 적용 범위 확인 이번 공식 실행 없음 |
| MASA Xu 등 WACV 2025 | [arXiv 원문](https://arxiv.org/html/2411.01040v1) 4절 식 3 individual unlearning 및 fusion | 개별 제출 모델의 망각 손실 이상 | 원문 확인 이번 공식 실행 없음 |
| BackdoorIndicator Li Dai 2024 | [학회 출처](https://www.usenix.org/conference/usenixsecurity24/presentation/li-songze) [원문](https://arxiv.org/html/2405.20862v1) 3절 | OOD 지표 작업을 학습 전에 삽입하는 능동 검사 | 원문 확인 사전 지표 삽입 없는 기존 체크포인트에는 소급 재현 불가 |
| FLAME Nguyen 등 2022 | [USENIX 원문](https://www.usenix.org/system/files/sec22-nguyen.pdf) Abstract 및 방어 구성 | 모델 군집화 클리핑 노이즈 집계 방어 | 원문 확인 이번 공식 실행 없음 |
| FedREDefense Xie Fang Gong 2024 | [ICML 공식 논문](https://proceedings.mlr.press/v235/xie24c.html) Abstract | 학습으로 재구성 가능한 업데이트인지 | 공식 출처 확인 이번 공식 실행 없음 |
| EBYD | [확장 원문](https://arxiv.org/html/2410.19427v1) IV A절 | clean unlearning으로 노출 후 탐지 정화 | 원문 확인 이번 공식 실행 없음 |
| UnlearnGuard 2025 | [원문](https://arxiv.org/html/2501.17396v1) Assumptions 1 2 및 Theorem 1 | 이력 기반 FU 업데이트 예측과 검증 | 원문 확인 이번 공식 실행 없음 |

## FedUBA가 연구 범위에 주는 수정

원문은 IEEE TDSC 23권 5호 10494–10510쪽이며 DOI는 `10.1109/TDSC.2026.3703139`다. 논문에 명시된 온라인 공개일은 2026년 6월 12일이고 현재 버전일은 9월 1일이다. 검색 사이트의 1월 표기보다 논문의 서지를 우선한다. [저자 원문](https://www.chenwang.net.cn/publications/FedUBA-TDSC26.pdf)

학습 이력에서 역할 쌍이 없더라도 삭제 입력이 과거 학습 입력과 다르거나 삭제의 효과가 왜곡되면 위험할 수 있다. 이 해석을 근거로 역할 관계 검사와 요청 일치성 검사를 다른 가설로 둔다. 단순 패치 기준선의 실패가 FedUBA의 방어 결과를 재현했다는 뜻은 아니다.

## 신규성 주장에 사용할 수 없는 부분

언러닝 기반 노출, non-IID 보정, 과거 업데이트 이용, 위장 후 삭제 활성화는 이미 존재한다. 새로운 연구 주장으로 남길 부분은 구체적인 관측 가정 아래에서 **정당한 위험 요청과 조작된 위험 요청을 구분하고 두 단계의 오류를 따로 검증하는 설계**다. 기존 HRAC intra 가설과의 연속성도 밝힌다. 새로운 이름이나 점수 조합만으로 독립 기여가 확정되지 않는다.
