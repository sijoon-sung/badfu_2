# 확정 BadFU 기준 체크포인트 · v1

**이 폴더가 앞으로 사용하는 고정 기준 모델입니다.** 고정 ID: `badfu.confirmed.s20261023.v1` · 학습 시드: `20261023` · 각 조건 최종 40라운드.

BadFU 핵심 구현을 저자 코드와 직접 비교했고, 아래 모델에서 **위장 데이터가 있을 때의 부분 억제 → 위장 데이터 제거 후 활성화**를 확인했습니다. 아래 6개 가중치는 원본과 바이트 단위로 같은 별도 사본입니다. 추가 학습이 진행되어도 이 버전은 교체하지 않습니다.

| 구분 | 파일 | 정상 정확도 | ASR | 평가 기준 |
|---|---|---:|---:|---|
| 삭제 전 · `pre` | [01_before_unlearning.pt](models/01_before_unlearning.pt) | 90.38% | 14.2889% | 저자 평가기, NCHW v2 |
| 위장 850장 제거 후 · `post` | [02_after_cover_removal_retrain.pt](models/02_after_cover_removal_retrain.pt) | 90.46% | 100% | 저자 평가기, NCHW v2 |
| 정상 학습 · `clean_pre` | [03_clean_reference.pt](models/03_clean_reference.pt) | 90.80% | 1.3889% | 저자 평가기, NCHW v2 |
| 정상 850장 제거 · `clean_post` | [04_clean_same850_removed.pt](models/04_clean_same850_removed.pt) | 90.33% | 1.3889% | 기존 channels-last 기록 |
| 큰 정상 참여자 제거 · `clean_big_post` | [05_clean_big_client_removed.pt](models/05_clean_big_client_removed.pt) | 89.76% | 1.6556% | 기존 channels-last 기록 |
| 공통 초기값 · `initial` | [00_shared_initial.pt](models/00_shared_initial.pt) | — | — | 모든 조건의 같은 초기값 |

정상 평가 10,000장, ASR 평가는 실제 타깃 클래스를 제외한 트리거 입력 9,000장입니다. 마지막 두 대조군의 기존 평가와 앞의 저자 형식 재평가를 구분해 보존했습니다.

## 확인된 범위

- 학습 데이터 99,150개의 정규화 픽셀·레이블, 원본 분할, 초기화, 핵심 함수가 저자 코드와 일치합니다. 삭제 전후 첫 라운드를 독립 계산해 10개 참여자 갱신과 두 전역 모델이 정확히 일치했습니다.
- 삭제 후 모델은 동일 초기값에서 위장 자료만 제거하고 유지 자료 전체를 재학습한 결과입니다. 근사 FedEraser 결과가 아닙니다.
- 삭제 전 ASR 14.29%는 부분 억제입니다. ASR≤10%의 강한 잠복 기준과 논문의 독립 3회 평균 수치까지 재현했다고 선언하지 않습니다.
- 이 폴더는 최종 모델 보관본입니다. 전체 라운드 및 개별 참여자 이력 연구에는 기존 `badfu.paper32.s20261020`을 명시적으로 선택합니다. FUBA는 이 승인에 포함되지 않습니다.

## 바로 확인하거나 불러오기

로컬 저장소 루트에서 6개 모델의 해시·텐서·실제 로딩을 확인합니다. 학습이나 데이터 다운로드는 실행하지 않습니다.

```powershell
.\envs\badfu-original\python.exe CONFIRMED_CHECKPOINTS\BadFU_s20261023_v1\load_confirmed.py --load-all
```

DISLAB에서도 같은 폴더의 `load_confirmed.py --load-all`을 실행할 수 있습니다. 경로는 `D:/CONFIRMED_CHECKPOINTS/BadFU_s20261023_v1`입니다.

Python에서는 이 폴더를 모듈 경로에 넣고 다음과 같이 사용합니다.

```python
import sys
sys.path.insert(0, r"C:\Users\sijoo\Documents\ChatGPT\badFU\CONFIRMED_CHECKPOINTS\BadFU_s20261023_v1")
from load_confirmed import load_model
pre = load_model("pre")
post = load_model("post")
```

`load_model`은 검증 후 평가 모드의 모델만 반환합니다. 입력 정규화는 저자 기준 CIFAR-10 정규화를 별도로 적용합니다. [MANIFEST.json](MANIFEST.json)의 `server_input_contract`를 따르고, ASR·타깃·트리거 등 평가 전용 정보는 방어 알고리즘에 전달하지 않습니다.

## 보존 규칙과 증거

파일은 읽기 전용 속성으로 보존합니다. 실험 결과와 수정 모델은 이 폴더 밖의 새 실험 폴더에 저장합니다. 변경된 결과는 새 버전으로 등록하며 v1을 덮어쓰지 않습니다.

[MANIFEST.json](MANIFEST.json)은 원본 경로·역할·전체 파일 SHA256을, [SEAL.json](SEAL.json)은 목록의 SHA256을 보관합니다. 이 해시는 연구 카탈로그의 별도 보존 증거에도 기록되어 있습니다. 로더는 불일치하면 중지합니다.

[저자 코드 직접 비교](evidence/README.md) · [독립 평가](evidence/FRESH_AUTHOR_EVALUATION.json) · [수치 비교](evidence/NUMERICAL_COMPARISON.csv) · [원본 선택 정보](provenance/source_case.json)

원본 경로와 과거 실패 기록은 그대로 보존했습니다. 이 폴더에는 CIFAR 원본 데이터와 전체 라운드 이력은 복제하지 않았습니다.
