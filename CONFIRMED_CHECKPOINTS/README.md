# 확정 체크포인트

**[BadFU 기준 체크포인트 v1 열기](BadFU_s20261023_v1/README.md)**

| 고정 ID | 검증한 결과 | 보관 내용 |
|---|---|---|
| `badfu.confirmed.s20261023.v1` | 삭제 전 ASR14.29% → 위장 제거 후100%; 정상 정확도90.38% → 90.46% | 삭제 전후·정상 대조3개·공통 초기값, 총6개 모델 |

이 폴더에는 바로 불러올 수 있는 실제 가중치 사본이 있습니다. 로컬과 DISLAB 양쪽에서 파일 해시, 모델 로딩, 텐서와 출력의 유한성을 확인하고 읽기 전용으로 보존했습니다.

- 로컬: `C:/Users/sijoo/Documents/ChatGPT/badFU/CONFIRMED_CHECKPOINTS/BadFU_s20261023_v1`
- DISLAB: `D:/CONFIRMED_CHECKPOINTS/BadFU_s20261023_v1`
- 검증·선택: [연구 카탈로그](../research/00_trajectories/README.md)

최종 모델 실험의 기본 입력은 위 고정 ID입니다. 전체 참여자 이력이 필요한 실험은 `badfu.paper32.s20261020`을 선택합니다. 새 실험과 수정 모델은 이 보관 폴더 밖에 저장합니다. 버전 v1은 교체하지 않습니다.

확정 범위는 BadFU 핵심 구현 비교와 부분 억제 후 활성화입니다. 논문3회 평균 수치의 완전 재현, ASR≤10%의 강한 잠복 기준, 근사 FedEraser 및 FUBA 재현은 이 승인에 포함되지 않습니다.
