# FUBA v2 중간 체크포인트 · 63/100라운드

**사용자 요청으로 학습 중 저장된 63라운드를 따로 복사한 실제 모델입니다.** 본100R 학습은 계속 진행합니다. 관련 카드: R02. 최종 공격 재현 판정은 미완료입니다.

- `checkpoint.pt`: 원본 라운드 전체 사본. 분류기는 `gm_after`, 집계 생성기는 `extras.aggregate_generator`입니다.
- `classifier.pt`, `aggregate_generator.pt`: 같은 라운드에서 추출한 bare state_dict입니다.
- `initial.pt`: 이 실행의 초기값입니다.
- `source/`: 해당 모델 구조와 실제 실행한 학습 코드 사본입니다. 학습 실행에는 DISLAB의 원본 데이터·환경이 필요합니다.
- `load_checkpoint.py`: 데이터나 GPU 없이 두 모델을 엄격하게 로딩하고 출력까지 확인합니다.

8개 참여자 상태를 포함한 저장 텐서, 배치 정규화, 인접 모델 연결을 확인했습니다. 집계 재구성 오차는0입니다. 최종100R 평가나 정상 대조·삭제 후 활성화의 완료를 뜻하지 않습니다.

로컬 저장소 루트에서:

```powershell
.\envs\badfu-original\python.exe CHECKPOINTS_FOR_REVIEW\FUBA_v2_s20261023_round0063\load_checkpoint.py
```

Python에서 이 폴더를 모듈 경로에 넣고 `from load_checkpoint import load_models` 후 `classifier, generator = load_models()`로 불러옵니다. 기본값은 CPU·평가 모드입니다.

실제 대상은 stcebra/FUBA v2이며 별도 ity207/FedUBA와 다릅니다. 생성기와 평가 전용 정보는 서버 탐지 알고리즘 입력에 전달하지 않습니다.
