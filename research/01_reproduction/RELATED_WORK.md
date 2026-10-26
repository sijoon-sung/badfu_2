# 기초 검토에 필요한 관련 연구

**2026년 10월 20일 우선 조사:** [역할 식별과 역할 식별 없는 정화의 선행 연구 비교](literature/20261020/PRIOR_WORK_AND_CLAIMS.md). FLForensics·FilterFL·FedSweep·SAU·EBYD·PAM을 중심으로 입력 조건, 기존 아이디어와의 중복, 두 연구 방향의 차별점 후보 및 한 줄 가설을 정리했다. 최신 문헌의 본문 확인이 남은 항목도 함께 표시했다.

논문 수를 늘리는 대신 각 문헌이 어떤 질문에 답하고 어떤 가정을 추가하는지 읽는다. 아래는 원문 또는 공식 초록·구현을 확인한 출발 문헌이다. 우리 조건의 성공·실패 결과를 승계하지 않는다.

| 문헌 | 먼저 읽을 내용 | 우리 문제에 가져올 점과 경계 |
|---|---|---|
| [UBA-Inf USENIX 2024](https://www.usenix.org/conference/usenixsecurity24/presentation/huang-zirui) | 위장을 삭제해 활성화하는 중앙집중형 공격 | 언러닝 활성화 자체는 선행 아이디어. FL의 권한·소유·집계가 더하는 문제를 분리 |
| [FedEraser IWQoS 2021](https://arxiv.org/abs/2012.13891v3) | 저장 갱신과 보정으로 삭제 모델을 재구성 | 단순 최종 기여 차감과 구분. 재학습 유사성과 보안의 차이를 검토 |
| [Influence Functions ICML 2017](https://proceedings.mlr.press/v70/koh17a.html) | 학습 샘플의 작은 가중 변화와 예측 영향 | H⁻¹ 기울기의 의미와 국소 근사 조건. 비선형 대규모 삭제를 그대로 인증하지 않음 |
| [Neural Cleanse S&P 2019 공식 구현](https://github.com/bolunwang/backdoor) | 타깃별 트리거 역합성과 이상치 판정 | 미지 트리거 탐지의 기본 비교. 역합성과 판정의 실패를 분리 |
| [MASA arXiv v1](https://arxiv.org/html/2411.01040v1) | 정상 과제를 잊히며 개별 모델 반응 관측, 모델 융합 | 정상 proxy 데이터가 필요하고 non-IID 반응 차이를 통제. 실제 삭제 요청의 분류와 같은 실험은 아님 |
| [UnlearnGuard arXiv v1](https://arxiv.org/html/2501.17396v1) | 이력 기반 FU 갱신 검사와 Theorem 1 | 정리는 FL 중 악성 참여자 탐지와 강볼록성 등의 조건부. 정직한 삭제로 남은 독성을 드러내는 문제와 구분 |
| [Fine-Pruning 2018](https://arxiv.org/abs/1805.12185) | 가지치기와 미세조정 결합 | 정상 표현과 공격 표현의 분리 가능성 및 효용 회복. 단순 SVD 제거를 이 방법 재현으로 세지 않음 |
| [SAU NeurIPS 2023](https://proceedings.neurips.cc/paper_files/paper/2023/hash/520425a5a4c2fb7f7fc345078b188201-Abstract.html) | 작은 정상 데이터와 공유 적대 예제를 이용한 정화 | 데이터와 탐색 예산을 맞춘 FU 후 정화의 비교 후보. 두 모델 사용 자체는 신규성이 아님 |

## 읽고 나서 적을 질문

각 논문에 대해 입력과 출력, 공격자 권한, 방어자가 보는 정보, 작동 단계, 이론 가정, 실제 비교군을 한 번씩 확인한다. 표에 없는 논문을 추가하려면 현재의 어느 가설이나 비교를 바꾸는지 먼저 적는다.

FUBA는 [별도 독해](fuba/README.md)에서 BadFU와 공격 단위를 비교한다. 공식 본문과 보충자료의 재확인이 필요한 세부 수치를 옛 노트에서 가져와 확정하지 않는다.
